"""

(C) Copyright 2014 David Darmann

Version 1.0 - September 2014 - for PiTFT 320x240 touchscreen

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation; either version 2 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA
02111-1307, USA.

Usage:
 - cd into containing folder
 - sudo python pisms.py

This must run as root (sudo python pisms.py) due to framebuffer, etc.

"""

from datetime import datetime, timedelta
import sys, signal
import pygame
from pygame.locals import *
from VKeyboard.virtualKeyboard import VirtualKeyboard
from time import sleep
import os
import fnmatch
import subprocess
from textrect import render_textrect, TextRectException
import gnupg_fixed as gnupg
import cPickle as pickle

import pisms_ui
from mobileBroadband import E303, IncompletePGP

phone_book_file= "phone_book.p"
keyserver= "pool.sks-keyservers.net"
gnupghomedir= "gnupg_pisms"
phone_prefix= "+43"    # for Austria

# Page functions ---------------------------------------------------------------
def pageStart(**kwargs):
    print 'StartPage'
    pisms_ui.page_data= {}


def pageInbox(page_nr=1, **kwargs):
    global passphrase
    print 'Inbox selected, loading messages. Page number is', page_nr
    initButtons(pageInbox)
    decryption_error= False
    if(page_nr is 1):
        try:
            modem.updateMessageCache()
        except IncompletePGP:
            if('ingore_incomplete' in kwargs and kwargs['ingore_incomplete']):
                print 'Inbox: Ignored incomplete PGP Message'
            else:
                pisms_ui.page= pageIncompletePGP
                return

    messages, nr_of_messages= modem.getPageOfMessages(page_nr, pisms_ui.messages_per_page)
    if not messages:
        print 'Inbox: modem error'
        txtFont = pygame.font.SysFont("opensans", 25)
        txt= txtFont.render('Error:', 1, txtColor)
        screen.blit(txt, (15, 15))
        
        txtFont = pygame.font.SysFont("opensans", 18)
        txt= txtFont.render('Communication with modem failed.', 1, txtColor)
        screen.blit(txt, (15, 50))    
        return    

    print 'Inbox: Got {} messages for this page.'.format(nr_of_messages)
    if messages:
        print 'Inbox: number of messages is', nr_of_messages
        vpos= 15
        txtFont = pygame.font.SysFont("opensans", 14)
        txtFont_big = pygame.font.SysFont("opensans", 25)
        showed_decrypt_message= False
        for index, message in enumerate(messages):
            #print message
            message_bg= 'message_bg'

            msg_surface= pygame.Surface((300,40), pygame.SRCALPHA)
            msg_surface.convert_alpha()
            
            phone= txtFont.render(message['phone'] , 1, txtColor)
            msg_surface.blit(phone, (30,0))

            date= txtFont.render(message['date'], 1, txtColor)
            msg_surface.blit(date, (155,0))
            
            if not message['content']: message['content']= ''

            if message['is_pgp']:
                print ("Inbox: Going to decrypt a message...")
                message_bg= 'message_lock_bg'
                if not showed_decrypt_message:
                    txt= txtFont_big.render('Decrypting...', 1, txtColor)
                    screen.blit(txt, (15, 15))
                    pygame.display.update()
                    showed_decrypt_message= True

                decrypt_result= gpg.decrypt(message['content'])
                if not decrypt_result.ok:
                    while decrypt_result.status == 'need passphrase':
                        try:
                            decrypt_result= gpg.decrypt(message['content'], passphrase= passphrase)
                        except NameError as e:
                            print "Inbox: NameError, args:", e.args
                            txt= txtFont_big.render('Please enter passphrase!', 1, txtColor)
                            screen.blit(txt, (15, 50))
                            pygame.display.update()
                            sleep(2)
                            getPassphrase()
                            screen.blit(bg, (0,0))
                            txt= txtFont_big.render('Decrypting...', 1, txtColor)
                            screen.blit(txt, (15,15))
                            pygame.display.update()

                    if not decrypt_result.ok:
                        #we've got a passphrase, but for some reason it still doesn't work.
                        print "Inbox: passphrase didn't work."                        
                        message['content']= "decryption failed"
                        decryption_error= True
                    else:
                        message['content']= str(decrypt_result).decode(encoding='UTF-8', errors='ignore')
                else:
                    message['content']= str(decrypt_result).decode(encoding='UTF-8', errors='ignore')
                    
            content_without_newlines= ' '.join(message['content'].split())
            content= txtFont.render(content_without_newlines, 1, txtColor)
            msg_surface.blit(content, (30, 18))

            buttons[pageInbox].append(pisms_ui.Button((10,vpos,300,40), bg=message_bg,
                np=pageMessageSingleView, fg= msg_surface,
                np_value={'message': message, 'page_nr': page_nr}))
            print "Inbox: just created a message button", message
            vpos+=50
        
        if(page_nr > 1):
            buttons[pageInbox].append(pisms_ui.Button((48,218,100,22), bg='btn_left', np=pageScrollMessages, np_value={'page_nr': page_nr-1}))

        next_page_messages= modem.getPageOfMessages(page_nr+1, pisms_ui.messages_per_page)[1]
        if(next_page_messages > 0):
            buttons[pageInbox].append(pisms_ui.Button((172,218,100,22), bg='btn_right', np=pageScrollMessages, np_value={'page_nr': page_nr+1}))
    else:
        txtFont = pygame.font.SysFont("opensans", 25)
        txt = txtFont.render('No messages to display.' , 1, txtColor)
        screen.blit(txt, (15, 15))
        pygame.display.update()

    if decryption_error:
        try:
            del passphrase
        except NameError:
            pass

        print "Inbox: deleted obviously incorrect passphrase."

def getPassphrase():
    global passphrase
    print "getPassphrase: please enter a passphrase!"
    vkey= VirtualKeyboard(screen)
    passphrase= vkey.run("")
    if passphrase is None:
        del passphrase
    print "getPassphrase: thank you!"

def pageIncompletePGP(**kwargs):
    txtFont = pygame.font.SysFont("opensans", 25)
    txt= txtFont.render('Error:', 1, txtColor)
    screen.blit(txt, (15, 15))
    
    txtFont = pygame.font.SysFont("opensans", 18)
    txt= txtFont.render('IncompletePGP Message.', 1, txtColor)
    screen.blit(txt, (15, 50))
    txt= txtFont.render('Maybe not all parts received yet?', 1, txtColor)
    screen.blit(txt, (15, 75))

    pygame.display.update()

    print 'IncompletePGP: Incomplete PGP Message, try again?'


def pageScrollMessages(**kwargs):
    pisms_ui.page= pageInbox


def pageMessageSingleView(message, page_nr):
    global buttons
    initButtons(pageMessageSingleView)
    
    print "MessageSingleView:", message

    buttons[pageMessageSingleView][1].np_value= {'page_nr': page_nr}    #allow go back to correct page

    msg_surface= pygame.Surface((300,198), pygame.SRCALPHA)
    msg_surface.convert_alpha()
    
    msg_surface.fill((255,255,255))
    msg_surface.fill((0,0,0), pygame.Rect(1,1,298, 196))

    txtFont = pygame.font.SysFont("opensans", 16)
    txtRect= pygame.Rect(10, 6, 280, 184)

    try:
        rendered_text = render_textrect(message['content'], txtFont, txtRect, (255, 255, 255), (0, 0, 0), 0)
    except TextRectException:
        print 'MessageSingleView: text to long'
        rendered_text = render_textrect("Error:\nCouldn't render text, doesn't fit", txtFont, txtRect, (255, 255, 255), (0, 0, 0), 0)

    msg_surface.blit(rendered_text, txtRect.topleft)
    screen.blit(msg_surface, (10,10))
    pygame.display.update()

    buttons[pageMessageSingleView].append(pisms_ui.Button((148, 218, 24, 22), bg='btn_trash', np=pageDeleteMessage,
        np_value={'message': message, 'page_nr': page_nr}))


def pageDeleteMessage(message, page_nr):
    txtFont = pygame.font.SysFont("opensans", 25)
    txt= txtFont.render('Deleting Message...', 1, txtColor)
    screen.blit(txt, (15, 15))
    pygame.display.update()

    delete_error= False
    while len(message['indices']) > 0:
        delete_index= message['indices'].pop()
        print "Should delete index", delete_index
        if modem.deleteMessage(delete_index) is True:
            print "Deleted message with index {} sucessfully".format(delete_index)
        else: delete_error= True

    if delete_error:
        txtFont = pygame.font.SysFont("opensans", 15)
        txt= txtFont.render(modem.getLastError(), 1, txtColor)
    else:
        txt = txtFont.render('Successful' , 1, txtColor)

    screen.blit(txt, (15, 65))
    pygame.display.update()

    sleep(2)
    del pisms_ui.page_data['message']
    pisms_ui.page_data['page_nr']= 1
    pisms_ui.page= pageInbox


def pageWriteMsg(key, **kwargs):
    global buttons
    initButtons(pageWriteMsg)
    print 'WriteMsg selected'
    print kwargs
    
    phone_book= pickle.load(open(phone_book_file, "rb"))
    txtFont = pygame.font.SysFont("opensans", 25)

    if not key['fingerprint'] in phone_book:
        txt= txtFont.render('Error:', 1, txtColor)
        screen.blit(txt, (15, 5))
        txtFont = pygame.font.SysFont("opensans", 18)
        txt= txtFont.render('No phone number found for', 1, txtColor)
        screen.blit(txt, (15, 40))
        txt= txtFont.render('selected key!', 1, txtColor)
        screen.blit(txt, (15, 65))
        pygame.display.update()
        buttons[pageWriteMsg].append(pisms_ui.Button((168, 130,  135, 98), bg='btn_key_mgmt_large', np=pageKeySingleView, np_value={'key': key, 'page_nr': kwargs['page_nr']}))
    else:
        phone= phone_book[key['fingerprint']]
        txt= txtFont.render('Send a Message to', 1, txtColor)
        screen.blit(txt, (15, 5))
        txtFont = pygame.font.SysFont("opensans", 18)
        name= key['uids'][0].split("<", 1)[0]

        txt= txtFont.render(name, 1, txtColor)
        screen.blit(txt, (15, 40))
        txt= txtFont.render(phone, 1, txtColor)
        screen.blit(txt, (15, 65))
        pygame.display.update()
        buttons[pageWriteMsg].append(pisms_ui.Button((168, 130,  135, 98), bg='btn_okay_large', np=pageSendMessage, np_value={'key': key, 'phone': phone}))


def pageSendMessage(key, phone, **kwargs):
    print "SendMessage selected"
    vkey = VirtualKeyboard(screen)
    message= vkey.run("")

    while not message.strip():      #force user to write something other than whitespace
        txtFont = pygame.font.SysFont("opensans", 22)
        txt= txtFont.render("Message mustn't be empty!", 1, txtColor)
        screen.blit(txt, (15,15))
        pygame.display.update()
        sleep(2)
        screen.blit(bg, bgRect)
        pygame.display.update()
        vkey = VirtualKeyboard(screen)
        message= vkey.run("")

    print "SendMessage: goint to encrypt."
    txtFont = pygame.font.SysFont("opensans", 25)
    txt= txtFont.render("Encrypting...", 1, txtColor)
    screen.blit(txt, (15,15))
    pygame.display.update()

    encrypted_ascii_data = gpg.encrypt(message, key['fingerprint'], always_trust=True)
    print encrypted_ascii_data

    txt= txtFont.render("Sending...", 1, txtColor)
    screen.blit(txt, (15,65))
    pygame.display.update()

    if(modem.sendMessage(encrypted_ascii_data, phone)):
        txt= txtFont.render("Successful", 1, txtColor)
    else:
        txt= txtFont.render("Failed", 1, txtColor)
    screen.blit(txt, (15,115))
    pygame.display.update()


def pageKeyMgmt(**kwargs):
    print 'KeyMgmt selected'


def pageAddKeys(**kwargs):
    print 'AddKey selected'
    vkey = VirtualKeyboard(screen)
    if 'search_string' in kwargs:
        search_string = vkey.run(kwargs['search_string'])
    else:
        search_string = vkey.run("")

    if search_string == None:
        pisms_ui.page= pageKeyMgmt
        return

    print "AddKey is searching for", search_string
    
    txtFont = pygame.font.SysFont("opensans", 25)
    txt= txtFont.render('Searching...', 1, txtColor)
    screen.blit(txt, (15, 15))
    pygame.display.update()
    
    search_result= gpg.search_keys(search_string, keyserver)
    print search_result

    if len(search_result) < 1:
        txt= txtFont.render('Sorry, no keys found.', 1, txtColor)
        screen.blit(txt, (15, 65))
        pygame.display.update()
    else:
        txt= txtFont.render("Found "+str(len(search_result))+" keys.", 1, txtColor)
        screen.blit(txt, (15, 65))
        pygame.display.update()
        pisms_ui.page_data= {'mode': 'add_keys', 'keys': search_result, 'search_string': search_string}
        pisms_ui.page= pageListKeys
        sleep(1)


def pageAddKey(key, **kwargs):
    txtFont = pygame.font.SysFont("opensans", 25)
    txt= txtFont.render('Importing Key...', 1, txtColor)
    screen.blit(txt, (15, 15))
    pygame.display.update()   

    import_result = gpg.recv_keys(keyserver, key['keyid'])

    print import_result

    pisms_ui.page= pageListKeys


def pageListKeys(page_nr= 1, mode='list_keys', **kwargs):
    global buttons
    #TODO: Add Pagination, page parameter
    initButtons(pageListKeys)
    print 'ListKeys selected'
    key_bg= 'key_bg'
    np_function= pageKeySingleView
    search_string= None
    keys= gpg.list_keys()

    if mode == 'list_keys':
        pass
    elif mode == 'add_keys':
        keys= kwargs['keys']
        search_string= kwargs['search_string']
        buttons[pageListKeys][1].next_page= pageAddKeys                     #manipulate back button
        buttons[pageListKeys][1].np_value= {'search_string': search_string} #manipulate back button
        key_bg='add_key_bg'
        np_function= pageAddKey
    elif mode == 'select_recipient':
        key_bg= 'write_to_key_bg'
        np_function= pageWriteMsg

    txtFont = pygame.font.SysFont("opensans", 14)
    vpos= 15

    number_of_keys= len(keys)
    print number_of_keys, "keys to show."

    if number_of_keys < 1:
        txtFont = pygame.font.SysFont("opensans", 25)
        txt = txtFont.render('No keys to display.' , 1, txtColor)
        screen.blit(txt, (15, 15))
        pygame.display.update()
        return

    start= (page_nr-1)*pisms_ui.messages_per_page
    end= page_nr*pisms_ui.messages_per_page
    print number_of_keys, "keys to show, doing from", start, "to", end

    for key in keys[start:end]:
        try:
            name, mail= key['uids'][0].split("<", 1)
        except ValueError:
            name= key['uids'][0]
            mail= '>'

        key_surface= pygame.Surface((300,40), pygame.SRCALPHA)
        key_surface.convert_alpha()
        
        uids= txtFont.render(name, 1, txtColor)
        key_surface.blit(uids, (50,0))
     
        mail= txtFont.render("<"+mail, 1, txtColor)
        key_surface.blit(mail, (50,18))

        buttons[pageListKeys].append(pisms_ui.Button((10,vpos,300,40), bg=key_bg,
            np=np_function, fg= key_surface,
            np_value={'key': key, 'page_nr': page_nr}))
        vpos+=50

    if(page_nr > 1):
        buttons[pageListKeys].append(pisms_ui.Button((48,218,100,22), bg='btn_left', np=pageScrollKeys,
            np_value={'keys': keys, 'page_nr': page_nr-1, 'mode': mode, 'search_string': search_string}))

    if(end < number_of_keys):
        buttons[pageListKeys].append(pisms_ui.Button((172,218,100,22), bg='btn_right', np=pageScrollKeys,
            np_value={'keys': keys, 'page_nr': page_nr+1, 'mode': mode, 'search_string': search_string}))

def pageScrollKeys(**kwargs):
    pisms_ui.page= pageListKeys

def pageKeySingleView(key, **kwargs):
    global buttons
    
    initButtons(pageKeySingleView)
    buttons[pageKeySingleView][1].np_value= {'page_nr': kwargs['page_nr']}

    phone_book= pickle.load(open("phone_book.p", "rb"))

    key_surface= pygame.Surface((300,198), pygame.SRCALPHA)
    key_surface.convert_alpha()
    
    key_surface.fill((255,255,255))
    key_surface.fill((0,0,0), pygame.Rect(1,1,298, 196))

    txtFont = pygame.font.SysFont("opensans", 16)
    txtRect= pygame.Rect(10, 6, 280, 184)

    print key

    if key['fingerprint'] in phone_book:
        phone_number= phone_book[key['fingerprint']]
    else:
        phone_number= 'None'

    txt= key['uids'][0] + "\n" + "KeyID: " + key['keyid'][8:] + "\n" + "Length: " + key['length'] + "\n\nPhone: " + phone_number
    try:
        rendered_text = render_textrect(txt, txtFont, txtRect, (255, 255, 255), (0, 0, 0), 0)
    except TextRectException:
        print 'KeySingleView: text to long'
        rendered_text = render_textrect("Error:\nCouldn't render text, doesn't fit", txtFont, txtRect, (255, 255, 255), (0, 0, 0), 0)

    key_surface.blit(rendered_text, txtRect.topleft)
    screen.blit(key_surface, (10,10))
    pygame.display.update()

    buttons[pageKeySingleView].append(pisms_ui.Button((96, 218, 24, 22), bg='btn_phone', np=pageEditPhone))
    buttons[pageKeySingleView].append(pisms_ui.Button((148, 218, 24, 22), bg='btn_trash', np=pageDeleteKey, np_value={'key': key}))


def pageDeleteKey(key, **kwargs):
    global buttons
    initButtons(pageDeleteKey)

    txtFont = pygame.font.SysFont("opensans", 25)
    txt= txtFont.render('Deleting Key...', 1, txtColor)
    screen.blit(txt, (15, 15))
    pygame.display.update()

    txtFont = pygame.font.SysFont("opensans", 18)
    private_keys= gpg.list_keys(True)
    this_is_a_private_key= False
    for private_key in private_keys:
        if private_key['fingerprint'] == key['fingerprint']:
            this_is_a_private_key= True
            break
    
    return_value= str(gpg.delete_keys(key['fingerprint']))

    if return_value != 'ok':
        txt= txtFont.render("Error: "+return_value, 1, txtColor)
        screen.blit(txt, (15, 50))
        if this_is_a_private_key:
            txt_question= txtFont.render("Do that now?", 1, txtColor)
            screen.blit(txt_question, (15, 75))
            buttons[pageDeleteKey].append(pisms_ui.Button(( 168, 130,  135, 98), bg='btn_okay_large',
                np=pagedeleteKeyPair, np_value={'key': key}))
            buttons[pageDeleteKey].append(pisms_ui.Button(( 15, 130,  135, 98), bg='btn_cancel_large',
                np=pageListKeys, np_value={}))
            return
    else:
        txt = txtFont.render('Successful' , 1, txtColor)
        screen.blit(txt, (15, 50))

    pygame.display.update()

    sleep(2)

    pisms_ui.page= pageListKeys
    pisms_ui.page_data= {}


def pagedeleteKeyPair(key, **kwargs):
    print "deleteKeyPair: going to delete a key including it's private key"

    txtFont = pygame.font.SysFont("opensans", 25)
    txt= txtFont.render('Deleting Keypair...', 1, txtColor)
    screen.blit(txt, (15, 15))
    pygame.display.update()

    return_value_sec= str(gpg.delete_keys(key['fingerprint'], True))

    if return_value_sec != 'ok':
        txt= txtFont.render("Error: "+return_value_sec, 1, txtColor)
        screen.blit(txt, (15, 50))
    else:
        return_value_pub= str(gpg.delete_keys(key['fingerprint']))
        if return_value_pub != 'ok':
            txt= txtFont.render("Error: "+return_value_pub, 1, txtColor)
            screen.blit(txt, (15, 50))
        else:
            # no errors
            print "deleteKeyPair: did that successfully"
            txt = txtFont.render('Successful' , 1, txtColor)
            screen.blit(txt, (15, 50))

    pisms_ui.page= pageListKeys
    pisms_ui.page_data= {}
    sleep(2)


def pageEditPhone(key, **kwargs):
    phone_book= pickle.load(open(phone_book_file, "rb"))
    if key['fingerprint'] in phone_book:
        old_phone_number= phone_book[key['fingerprint']]
    else: old_phone_number= phone_prefix

    print "EditPhone selected for key: " + key['uids'][0]
    vkey = VirtualKeyboard(screen)
    new_phone_number = vkey.run(old_phone_number)

    print "Input: {}".format(new_phone_number)

    if new_phone_number != None and new_phone_number != old_phone_number:
        print "EditPhone: going to update phone book..."
        if new_phone_number == '' and key['fingerprint'] in phone_book:
            del phone_book[key['fingerprint']]
        else:
            phone_book[key['fingerprint']]= new_phone_number
    
        pickle.dump(phone_book, open(phone_book_file, "wb"))
    else:
        print "EditPhone: nothing changed"
    pisms_ui.page= pageKeySingleView

def pageImportPrivateKey(**kwargs):
    global buttons
    initButtons(pageImportPrivateKey)
    print "ImportPrivateKey selected"
    txtFont = pygame.font.SysFont("opensans", 25)

    # check if there is an usb drive connected
    try:
        usb_drives= subprocess.check_output("ls /dev/sd*", shell= True, stderr=subprocess.STDOUT).splitlines()
    except subprocess.CalledProcessError as e:
        if "No such file or directory" in e.output:
            print "ImportPrivateKey: Sorry, no USB drives connected"
            txt= txtFont.render('Error:', 1, txtColor)
            screen.blit(txt, (15, 15))
            
            txtFont = pygame.font.SysFont("opensans", 18)
            txt= txtFont.render('No USB drives connected.', 1, txtColor)
            screen.blit(txt, (15, 50))
            pygame.display.update()

            buttons[pageImportPrivateKey].append(pisms_ui.Button((168, 100,  135, 98), bg='btn_retry', np=pageRefreshImportPrivateKey))
            buttons[pageImportPrivateKey].append(pisms_ui.Button((15, 100,  135, 98), bg='btn_cancel_large', np=pageKeyMgmt))
            return

    # check if it is already mounted
    try:
        already_mounted= subprocess.check_output("df -h | grep /mnt/usb", shell= True)
    except subprocess.CalledProcessError:
        already_mounted= False

    # if not, mount it!
    if not already_mounted:
        # check if mount directory exists
        try:
            subprocess.check_output(["ls", "/mnt/usb"], stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            if "No such file or directory" in e.output:
                print "ImportPrivateKey: creating mount directory..."
                subprocess.check_output(["mkdir", "/mnt/usb"])
        # mount
        print "ImportPrivateKey: mounting..."
        subprocess.check_output("mount -t vfat "+usb_drives[-1]+" /mnt/usb", shell= True)
    else:
        print "ImportPrivateKey: USB Drive already mounted."

    # check all files on root level and smaller than 10,000 bytes if they contain a key
    for root, dirs, files in os.walk('/mnt/usb', topdown=False):
        print "ImportPrivateKey: doing walk, root:", root, "dirs:", dirs, "files:", files
        for name in files:
            # looping through files on root level
            f = os.path.join(root, name)
            print "ImportPrivateKey: checking file", f
            if os.path.getsize(f) < 100000:
                # check if file contains keys
                scan_result= gpg.scan_keys(f)
                number_of_keys_in_file= len(scan_result)
                if number_of_keys_in_file > 0:
                    # file contains at least one key
                    print "ImportPrivateKey: file", "'"+name+"'", "contains", number_of_keys_in_file, "keys."
                    keyfile= open(f, 'r')
                    found_private_key= False
                    for key in scan_result:
                        if key['type'] == 'sec':
                            found_private_key= True
                    if not found_private_key:
                        # there is no private key, but at least one public key. Maybe the user wants to import that?
                        print "ImportPrivateKey: Keyfile didn't contain a private key."
                        txt= txtFont.render('Error:', 1, txtColor)
                        screen.blit(txt, (15, 15))
                        
                        txtFont = pygame.font.SysFont("opensans", 18)
                        txt= txtFont.render('Found keyfile without a private key.', 1, txtColor)
                        screen.blit(txt, (15, 50))
                        txt= txtFont.render('Import public key(s) anyway?', 1, txtColor)
                        screen.blit(txt, (15, 75))
                        pygame.display.update()

                        buttons[pageImportPrivateKey].append(pisms_ui.Button(( 168, 130,  135, 98), bg='btn_okay_large',
                            np=pageImportKey, np_value={'key_ascii': keyfile.read()}))
                        buttons[pageImportPrivateKey].append(pisms_ui.Button(( 15, 130,  135, 98), bg='btn_cancel_large',
                            np=pageImportKey, np_value={'key_ascii': ''}))
                    else:
                        # so we found a keyfile that contains a private key. Import!
                        print "ImportPrivateKey: Keyfile does contain at least one private key."
                        txt= txtFont.render('Success:', 1, txtColor)
                        screen.blit(txt, (15, 15))
                        txtFont = pygame.font.SysFont("opensans", 18)
                        txt= txtFont.render('Found keyfile holding private key.', 1, txtColor)
                        screen.blit(txt, (15, 50))
                        pygame.display.update()
                        pisms_ui.page= pageImportKey
                        pisms_ui.page_data= {'key_ascii': keyfile.read()}
                        sleep(2)

                    keyfile.close()
                    break
                else:
                    print "ImportPrivateKey:", "'"+name+"'", "wasn't a keyfile"
    try:
        subprocess.check_output("umount /mnt/usb", shell= True)
    except subprocess.CalledProcessError:
        print "ImportPrivateKey: couldn't unmount usb drive."
    else:
        print "ImportPrivateKey: done, unmounted"

def pageImportKey(key_ascii, **kwargs):
    print "pageImportKey: going to import a key..."
    import_result= gpg.import_keys(key_ascii)
    print "pageImportKey:", import_result.count, "keys successfully imported."
    txtFont = pygame.font.SysFont("opensans", 25)
    plural_s= 's'
    if import_result.count == 1: plural_s= ''
    txt= txtFont.render('Imported '+str(import_result.count)+' key'+plural_s+'.', 1, txtColor)
    screen.blit(txt, (15, 15))
    pygame.display.update() 
    pisms_ui.page= pageKeyMgmt
    sleep(2)

def pageRefreshImportPrivateKey(**kwargs):
    pisms_ui.page= pageImportPrivateKey


def pageShutdown(**kwargs):
    print 'Going down...'
    subprocess.call(['sudo', 'shutdown', '-h', 'now'])
    sys.exit(0)

#  -----------------------------------------------------------------------------


# Button definitions -----------------------------------------------------------
buttons= {}
def initButtons(page= None):
    global buttons
    
    if not page or page == pageStart:
        buttons[pageStart]= [
            pisms_ui.Button(( 15, 15,  135, 120), bg='btn_show_inbox',     np=pageInbox),
            pisms_ui.Button((168, 15,  135, 120), bg='btn_write_message',  np=pageListKeys, np_value={'mode': 'select_recipient'}),
            pisms_ui.Button(( 15, 154, 290,  53), bg='btn_key_management', np=pageKeyMgmt),
            pisms_ui.Button((296, 218,  24,  22), bg='btn_off',            np=pageShutdown),
        ]

    if not page or page == pageInbox:
        buttons[pageInbox]= [
            pisms_ui.Button((  0, 218,  24,  22), bg='btn_home',           np=pageStart),
            pisms_ui.Button((296, 218,  24,  22), bg='btn_refresh2',       np=pageInbox, np_value={'page_nr': 1}),            
        ]

    if not page or page == pageIncompletePGP:
        buttons[pageIncompletePGP]= [
            pisms_ui.Button(( 15, 130,  135, 98), bg='btn_retry',          np=pageInbox),
            pisms_ui.Button((168, 130,  135, 98), bg='btn_ignore',         np=pageInbox, np_value={'page_nr': 1, 'ingore_incomplete': True}),
        ]

    if not page or page == pageWriteMsg:
        buttons[pageWriteMsg]= [
            pisms_ui.Button(( 15, 130,  135, 98), bg='btn_back_large',     np=pageListKeys, np_value={'mode': 'select_recipient'}),
        ]

    if not page or page == pageSendMessage:
        buttons[pageSendMessage]= [
            pisms_ui.Button((  0, 218,  24,  22), bg='btn_home',           np=pageStart),
        ]

    if not page or page == pageKeyMgmt:
        buttons[pageKeyMgmt]= [
            pisms_ui.Button((  0, 218,  24,  22), bg='btn_home',           np=pageStart),
            pisms_ui.Button(( 15, 15,  135, 120), bg='btn_list_keys',      np=pageListKeys),
            pisms_ui.Button((168, 15,  135, 120), bg='btn_add_key',        np=pageAddKeys),
            pisms_ui.Button(( 15, 154, 290,  53), bg='btn_import_private_key', np=pageImportPrivateKey),
        ]

    if not page or page == pageListKeys:
        buttons[pageListKeys]= [
            pisms_ui.Button((  0, 218,  24,  22), bg='btn_home',           np=pageStart),
            pisms_ui.Button((296, 218,  24,  22), bg='btn_back',           np=pageKeyMgmt),
        ]

    if not page or page == pageKeySingleView:
        buttons[pageKeySingleView]= [
            pisms_ui.Button((  0, 218,  24,  22), bg='btn_home',           np=pageStart),
            pisms_ui.Button(( 48, 218,  24,  22), bg='btn_back',           np=pageListKeys),
        ]

    if not page or page == pageDeleteKey:
        buttons[pageDeleteKey]= []

    if not page or page == pageEditPhone:
        buttons[pageEditPhone]= [],

    if not page or page == pageAddKeys:
        buttons[pageAddKeys]= [
            pisms_ui.Button((  0, 218,  24,  22), bg='btn_home',           np=pageStart),
            pisms_ui.Button(( 48, 218,  24,  22), bg='btn_back',           np=pageKeyMgmt),
        ]

    if not page or page == pageMessageSingleView:
        buttons[pageMessageSingleView]= [
            pisms_ui.Button((  0, 218,  24,  22), bg='btn_home',           np=pageStart),
            pisms_ui.Button(( 48, 218,  24,  22), bg='btn_back',           np=pageInbox),
        ]

    if not page or page == pageImportPrivateKey:
        buttons[pageImportPrivateKey]= []

    if not page or page == pageImportKey:
        buttons[pageImportKey]= []


initButtons()
#  -----------------------------------------------------------------------------


# Initialization ---------------------------------------------------------------

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
size = width, height = 320, 240
screen = pygame.display.set_mode(size)

# Display Welcome Screen
print "Welcome Screen"
bg_raw= pygame.image.load('background.png').convert()
bg= pygame.transform.scale(bg_raw, size)
bgRect = bg.get_rect()

screen.blit(bg, bgRect)

txtColor = (255,255,255)
txtFont = pygame.font.SysFont("opensans", 40)
txt = txtFont.render('PiSMS' , 1, txtColor)
screen.blit(txt, (15, 105))

txtFont = pygame.font.SysFont("opensans", 25)
txt = txtFont.render('PGP encrypted SMS App' , 1, txtColor)
screen.blit(txt, (15, 155))
pygame.display.update()

# Modem Initialization
modem= E303('192.168.1.1', pisms_ui.messages_per_page)

# GPG Initialization
gpg= gnupg.GPG(gnupghome=gnupghomedir, verbose= False)

# Check phone book
if not os.path.isfile(phone_book_file):
    phone_book= {}
    pickle.dump(phone_book, open(phone_book_file, "wb"))
    print "Created empty phone book"

print 'Sleeping...'
sleep(3)

print "Done, let's go!"
screen.blit(bg, bgRect)
pygame.display.update()


# Signal Handling ------------------------------------------------------------------------------

def Exit():
    print 'Exit'
#    StopAll()
    sys.exit(0)

def signal_handler(signal, frame):
    print 'SIGNAL {}'.format(signal)
    Exit()

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGHUP, signal_handler)
signal.signal(signal.SIGQUIT, signal_handler)



# Main Loop --------------------------------------------------------------------

pisms_ui.page = pageStart

while(True):

    try:
        pygame.event.get()
        screen.blit(bg, bgRect)
        pygame.display.update()
        current_page= pisms_ui.page
        
        # let the page do it's work
        pisms_ui.page(**pisms_ui.page_data)
        
        # draw buttons defined for page
        for button in buttons[pisms_ui.page]:
            button.draw(screen)
        pygame.display.update()
        
        # wait for user to push a button
        while pisms_ui.page == current_page:
            event= pygame.event.poll()
            if(event.type is MOUSEBUTTONDOWN):
                for button in buttons[pisms_ui.page]:
                    if button.selected(event.pos, screen):
                        current_page= None       #To make sure outer loop breaks too
                        break

        print 'MainLoop: Done, go for another run...'

    except SystemExit:
        print 'SystemExit'
        sys.exit(0)
    except:
        print '"Except:', sys.exc_info()[0]
        #    print traceback.format_exc()
        #    StopAll()
        raise

