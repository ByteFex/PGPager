import os
from pygame.locals import *
import pygame
from time import sleep


page= None
page_data= {}
messages_per_page= 4

# UI classes ---------------------------------------------------------------


class Icon(object):
    iconPath= 'icons'
    def __init__(self, name):
        self.name = name
        path= os.path.join(self.iconPath, name+'.png')
        try:
            self.bitmap = pygame.image.load(path)
        except:
            print "Couldn't load icon", path
            raise


class Button(object):
    def __init__(self, rect, **kwargs):
        self.rect        = rect # Bounds
        self.color       = None # Background fill color, if any
        self.iconBg      = None # Background Icon (atop color fill)
        self.surfaceFg   = None # Foreground surface (atop background)
        self.next_page   = None # next page
        self.np_value    = {}   # value for next page function
        for key, value in kwargs.iteritems():
            if   key == 'color': self.color    = value
            elif key == 'bg'   :
                if os.path.isfile(os.path.join(Icon.iconPath, value+'.png')):
                    self.iconBg= Icon(value)
            elif key == 'np'   : self.next_page = value
            elif key == 'fg'   : self.surfaceFg= value
            elif key == 'np_value': self.np_value= value

    def selected(self, pos, screen):
        global page, page_data

        x1 = self.rect[0]
        y1 = self.rect[1]
        x2 = x1 + self.rect[2] - 1
        y2 = y1 + self.rect[3] - 1
        if ((pos[0] >= x1) and (pos[0] <= x2) and
          (pos[1] >= y1) and (pos[1] <= y2)):

            self.overlay= pygame.Surface((self.rect[2], self.rect[3]))
            self.overlay.fill((255, 255, 255))
            self.overlay.set_alpha(127)
            screen.blit(self.overlay, (self.rect[0], self.rect[1]))
            pygame.display.update()

            while pygame.event.poll().type != MOUSEBUTTONUP:
                sleep(0)

            if self.next_page:
                page= self.next_page
                if len(self.np_value) > 0:
                    page_data= self.np_value

            return True
        return False

    def draw(self, screen):
        if self.color:
            screen.fill(self.color, self.rect)
        if self.iconBg:
            screen.blit(self.iconBg.bitmap,
              (self.rect[0]+(self.rect[2]-self.iconBg.bitmap.get_width())/2,
              self.rect[1]+(self.rect[3]-self.iconBg.bitmap.get_height())/2))
        if self.surfaceFg:
            screen.blit(self.surfaceFg, (self.rect[0], self.rect[1]))