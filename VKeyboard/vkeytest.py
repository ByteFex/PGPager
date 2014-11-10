#!/usr/bin/python

from datetime import datetime, timedelta
import sys, signal
import pygame
from pygame.locals import *
from virtualKeyboard import VirtualKeyboard
from time import sleep

import os


# Init framebuffer/touchscreen environment variables

# for Adafruit PiTFT:
os.putenv('SDL_VIDEODRIVER', 'fbcon')
os.putenv('SDL_FBDEV'      , '/dev/fb1')
os.putenv('SDL_MOUSEDRV'   , 'TSLIB')
os.putenv('SDL_MOUSEDEV'   , '/dev/input/touchscreen')

# Init pygame and screen
pygame.display.init()
pygame.font.init()
pygame.mouse.set_visible(False)

size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
print "Framebuffer size: %d x %d" % (size[0], size[1])

modes = pygame.display.list_modes(16)
screen = pygame.display.set_mode(modes[0], FULLSCREEN, 16)
size = (320,240)
screen = pygame.display.set_mode(size)


image = pygame.Surface.convert(pygame.image.load('background2.png'))
bg  = pygame.transform.scale(image, size)

bgRect = bg.get_rect()
txtColor = (255,255,255)
txtFont = pygame.font.SysFont("opensans", 40)
txt = txtFont.render('PiSMS' , 1, txtColor)
bg.blit(txt, (15, 105))

txtFont = pygame.font.SysFont("opensans", 25)
txt = txtFont.render('PGP encrypted SMS App' , 1, txtColor)
bg.blit(txt, (15, 155))


screen.blit(bg, bgRect)
pygame.display.update()
sleep(5)

#  ----------------------------------------------------------------

def Exit():
    print 'Exit'
#    StopAll()
    sys.exit(0)

def signal_handler(signal, frame):
    print 'SIGNAL {}'.format(signal)
    Exit()

def pageInputTest():
  global page
  print 'InputTest'
  while page == pageInputTest:
    vkey = VirtualKeyboard(screen) # create a virtual keyboard
    tn = datetime.now() + timedelta(seconds=5) # set ahead a bit
    txt = vkey.run(tn.strftime('%Y-%m-%d %H:%M:%S'))
    print 'input: {}'.format(txt)
    sleep(2); # or switch page...
    sys.exit();
    return

#  ----------------------------------------------------------------
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)
signal.signal(signal.SIGQUIT, signal_handler)

page = pageInputTest

while(True):

  try:
    page()

  except SystemExit:
#    print 'SystemExit'
    sys.exit(0)
  except:
    print '"Except:', sys.exc_info()[0]
#    print traceback.format_exc()
#    StopAll()
    raise

