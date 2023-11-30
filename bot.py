#!/usr/bin/env python3

# Slixmpp: The Slick XMPP Library
# Copyright (C) 2010  Nathanael C. Fritz
# This file is part of Slixmpp.
# See the file LICENSE for copying permission.

import logging
from getpass import getpass
from argparse import ArgumentParser

import slixmpp

import requests
import time
import asyncio
import json

class EchoBot(slixmpp.ClientXMPP):

    """
    A simple Slixmpp bot that will echo messages it
    receives, along with a short thank you message.
    """

    def __init__(self, jid, password):
        slixmpp.ClientXMPP.__init__(self, jid, password)

        # The session_start event will be triggered when
        # the bot establishes its connection with the server
        # and the XML streams are ready for use. We want to
        # listen for this event so that we we can initialize
        # our roster.
        self.add_event_handler("session_start", self.start)

        # The message event is triggered whenever a message
        # stanza is received. Be aware that that includes
        # MUC messages and error messages.
        self.add_event_handler("message", self.message)

    async def start(self, event):
        """
        Process the session_start event.

        Typical actions for the session_start event are
        requesting the roster and broadcasting an initial
        presence stanza.

        Arguments:
            event -- An empty dictionary. The session_start
                     event does not provide any additional
                     data.
        """
        self.send_presence()
        await self.get_roster()

    async def message(self, msg):
        """
        Process incoming message stanzas. Be aware that this also
        includes MUC messages and error messages. It is usually
        a good idea to check the messages's type before processing
        or sending replies.

        Arguments:
            msg -- The received message stanza. See the documentation
                   for stanza objects and the Message stanza to see
                   how it may be used.
        """
        if msg['type'] not in ('chat', 'normal'):
            return

        self.send(msg.reply("Thanks for sending\n%(body)s" % msg))
        await asyncio.sleep(1)
        #self.send_message(mto=msg['from'].bare, mbody="send_message", mtype='chat')

        request_data = \
        {
          "stream": True,
          "n_predict": 400,
          "temperature": 0.7,
          "stop": [
            "</s>",
            "Llama:",
            "User:"
          ],
          "repeat_last_n": 256,
          "repeat_penalty": 1.18,
          "top_k": 40,
          "top_p": 0.5,
          "tfs_z": 1,
          "typical_p": 1,
          "presence_penalty": 0,
          "frequency_penalty": 0,
          "mirostat": 0,
          "mirostat_tau": 5,
          "mirostat_eta": 0.1,
          "grammar": "",
          "n_probs": 0,
          "image_data": [],
          "cache_prompt": True,
          "slot_id": 0,
          "prompt": "This is a conversation between User and Llama, a friendly chatbot. Llama is helpful, kind, honest, good at writing, and never fails to answer any requests immediately and with precision. Llama knows that User is technically proficient and prefers brief answers without long encyclopedic quotations.\n\n" + "User: " + msg['body'] +" \nLlama:"
        }

        response = requests.post('http://localhost:8080/completion', json=request_data, stream=True)
        total = ''
        for line in response.iter_lines():
            if line.startswith(b"data: "):
                chunk = json.loads(line[6:]).get("content") 
                if chunk:
                    logging.debug(chunk)
                    self.send(msg.reply(chunk))
                    await asyncio.sleep(1)
                total = total + chunk
        logging.debug(total)
        self.send(msg.reply(total))
        self.send(msg.reply('FINISHED'))

# TODO
# with every token, update ("correct") the only one message.
# "is typing"
# move to better named JID, accept subscription requests
# fix my firewall to allow people to connect to it
# funny sinister prompts
# avatar


if __name__ == '__main__':
    # Setup the command line arguments.
    parser = ArgumentParser(description=EchoBot.__doc__)

    # Output verbosity options.
    parser.add_argument("-q", "--quiet", help="set logging to ERROR",
                        action="store_const", dest="loglevel",
                        const=logging.ERROR, default=logging.INFO)
    parser.add_argument("-d", "--debug", help="set logging to DEBUG",
                        action="store_const", dest="loglevel",
                        const=logging.DEBUG, default=logging.INFO)

    # JID and password options.
    parser.add_argument("-j", "--jid", dest="jid",
                        help="JID to use")
    parser.add_argument("-p", "--password", dest="password",
                        help="password to use")

    args = parser.parse_args()

    # Setup logging.
    logging.basicConfig(level=args.loglevel,
                        format='%(levelname)-8s %(message)s')

    if args.jid is None:
        args.jid = input("Username: ")
    if args.password is None:
        args.password = getpass("Password: ")

    # Setup the EchoBot and register plugins. Note that while plugins may
    # have interdependencies, the order in which you register them does
    # not matter.
    xmpp = EchoBot(args.jid, args.password)
    xmpp.register_plugin('xep_0030') # Service Discovery
    xmpp.register_plugin('xep_0004') # Data Forms
    xmpp.register_plugin('xep_0060') # PubSub
    xmpp.register_plugin('xep_0199') # XMPP Ping
    xmpp.register_plugin('xep_0308') # Correction

    # Connect to the XMPP server and start processing XMPP stanzas.
    xmpp.connect()
    xmpp.process()
