#!/bin/python2.7
"""Sonos player.

Keyboard controls:
    p: pause currently playing track
    s: stop playing current track
    l: increase volume
    q: decrease volume
"""

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
import argparse
from random import shuffle
import os
import sys
import time
import readchar
from urllib import quote
from threading import Thread
from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer import TCPServer
from soco.discovery import by_name, discover


class HttpServer(Thread):
    """A simple HTTP Server in its own thread"""

    def __init__(self, docroot, port):
    	os.chdir(docroot)
        super(HttpServer, self).__init__()
        self.daemon = True
        handler = SimpleHTTPRequestHandler
        self.httpd = TCPServer(("", port), handler)

    def run(self):
        """Start the server"""
        #print('Start HTTP server')
        self.httpd.serve_forever()

    def stop(self):
        """Stop the server"""
        #print('Stop HTTP server')
        self.httpd.socket.close()


def controller(zone):
    """Control currently playing track."""
    keep_polling = True
    paused = False
    while keep_polling:
    	device_state = zone.get_current_transport_info()['current_transport_state']
    	control_input = readchar.readchar()
	if control_input.lower() == 's':
	    # stop track
	    zone.stop()
	    print '\tSTOPPED'
	    keep_polling = False
	    continue
	elif control_input.lower() == 'p' and device_state == 'PAUSED_PLAYBACK':
	    # unpause
	    zone.play()
	    print '\tRESUME'
	elif control_input.lower() == 'p' and device_state == 'PLAYING':
	    zone.pause()
	    print '\tPAUSED'
	elif control_input.lower() == 'l':
	    zone.volume += 1
	    print '\tVOLUME ({}) +'.format(zone.volume)
	elif control_input.lower() == 'q':
	    zone.volume -= 1
	    print '\tVOLUME ({}) -'.format(zone.volume)
	time.sleep(0.2)
	    


def play_tracks(port, args, here, zone, docroot):
    """Play audio tracks."""
    # shuffle playlist
    playlist = args.files
    if args.random:
    	shuffle(playlist)

    base_url = 'http://10.0.0.1:{p}'.format(p=port)
    url_path = here.replace(docroot, '')
    url = base_url + url_path
    total_tracks = len(playlist)
    track_counter = 0
    for mp3 in playlist:
    	control_thread = Thread(target=controller, args=(zone,))
	control_thread.start()
    	track_counter += 1
	mp3_url = '{u}/{m}'.format(u=url, m=quote(mp3))
	print 'Adding to queue:\t{}'.format(mp3_url)
	print 'Playing track:\t{} of {}'.format(track_counter, total_tracks)
	try:
	    zone.play_uri(uri=mp3_url, title='test00101')
	except Exception as err:
	    print 'Failed to play {} due to error:\t{}'.format(mp3, err)
	    continue
	duration = zone.get_current_track_info()['duration']
	while zone.get_current_transport_info()['current_transport_state'] != 'STOPPED':
	    # wait for track to finish playing
	    time.sleep(1)
	    position = zone.get_current_track_info()['position']
	    # print current progress /duration
	    sys.stdout.write('\r{p} / {d}'.format(p=position, d=duration))
	    sys.stdout.flush()
	control_thread.join()


def main():
    # Settings
    port = 61823
    args = parse_args()
    docroot = args.docroot
    here = os.getcwd()

    # Get the zone
    zone = by_name(args.zone)

    # Check if a zone by the given name was found
    if zone is None:
        zone_names = [zone_.player_name for zone_ in discover()]
        print("No Sonos player named '{}'. Player names are {}"\
              .format(args.zone, zone_names))
        sys.exit(1)

    # Check whether the zone is a coordinator (stand alone zone or
    # master of a group)
    if not zone.is_coordinator:
        print("The zone '{}' is not a group master, and therefore cannot "
              "play music. Please use '{}' in stead"\
              .format(args.zone, zone.group.coordinator.player_name))
        sys.exit(2)
    if args.party:
    	zone.partymode()

    # Setup and start the http server
    server = HttpServer(docroot, port)
    server.start()

    zone.clear_queue()
    try:
        play_tracks(port, args, here, zone, docroot)
    except KeyboardInterrupt:
    	server.stop()
    zone.clear_queue()
    print '\n'


def parse_args():
    """Parse the command line arguments"""
    description = 'Play local files with Sonos by running a local web server'
    description += '\n\nKeyboard controls:\n\tp: pause currently playing track'
    description += '\n\ts: stop playing current track'
    description += '\n\tl: increase volume'
    description += '\n\tq: decrease volume'
    parser = argparse.ArgumentParser(description=description,
            	    	    	     formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('--zone', '-z', help='The name of the zone to play from',
    	    	    	required=True)
    parser.add_argument('--files', '-f', help='Space separated list of files to play',
    	    	    	nargs='+', required=True)
    parser.add_argument('--party', '-p', default=False, action='store_true',
    	    	    	help='play on all zones')
    parser.add_argument('--random', '-r', action='store_true', default=False,
    	    	    	help='randomize the order of tracks')
    parser.add_argument('--docroot', '-d', action='store', default='/media0/music',
    	    	    	help='Embedded web server doc root. All mp3 files must be' +
			' under this directory hierarchy')
    return parser.parse_args()


main()
