#! /usr/bin/env python

"""

(C) Copyright 2014 David Darmann

Version 1.0 - September 2014 - Basic API for Huawei E303 (and others)

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

"""

import abc
import requests
import xml.etree.ElementTree as ET
import datetime


class IncompletePGP(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)



class usbDongle(object):
    __metaclass__= abc.ABCMeta

    @abc.abstractmethod
    def updateMessageCache(self):
        while False:
            yield None

    @abc.abstractmethod
    def getPageOfMessages(self, page, messages_per_page):
        while False:
            yield None        

    @abc.abstractmethod
    def deleteMessage(self, index):
        while False:
            yield None



class E303(usbDongle):

    def __init__(self, ip, messages_per_page):
        #TODO: check IP, working
        self.ip= ip
        self.api_url= "http://"+ip+"/api"
        self.xml_header= '<?xml version="1.0" encoding="UTF-8"?>'
        self.timeout= 3
        self.error_msg= ''
        self.messages_per_page= messages_per_page
        self.message_cache= []
        self.messages_per_request= 20

    def __str__(self):
        return "IP: {}, API-URL: {}".format(self.ip, self.api_url)

    def error(self, error_msg):
        self.error_msg= error_msg
        print error_msg

    def getLastError(self):
        return self.error_msg

    def getMessages(self, page_index= 1):
        url= self.api_url+"/sms/sms-list"
        post_data= self.xml_header + """
            <request>
                <PageIndex>{}</PageIndex>
                <ReadCount>{}</ReadCount>
                <BoxType>1</BoxType>
                <SortType>0</SortType>
                <Ascending>0</Ascending>
                <UnreadPreferred>0</UnreadPreferred>
            </request>""".format(page_index, self.messages_per_request)
        try:
            r= requests.post(url, data= post_data, timeout= self.timeout)
        except requests.exceptions.Timeout:
            self.error("The request timed out while trying to connect to the remote server. It took longer than "+str(self.timeout)+" seconds.")
            return [False, False]
        except requests.exceptions.ConnectionError:
            self.error("A Connection error occurred.")
            return [False, False]
        else:
            xml_string= r.content.decode('utf-8', errors= 'ignore')
            xml_string= xml_string.encode('utf-8')
            # print str(xml_string)
            # print repr(xml_string)
            #print xml_string
            root = ET.fromstring(xml_string)
            if root.tag == 'error':
                self.error(self.__class__.__name__+" returned error {}.".format(root.text))
                return [False, False]
            
            count= root.find('Count')
            nr_of_messages= int(count.text)
            #print "Found", nr_of_messages, "messages."

            if nr_of_messages > 0:
                messages= root.find('Messages')
                message_list= []
                for message in messages:
                    message_list.append({
                        'indices': [int(message.find('Index').text)],
                        'date':    message.find('Date').text, 
                        'phone':   message.find('Phone').text, 
                        'content': message.find('Content').text,
                        'type':    message.find('SmsType').text,
                        'is_pgp':  False
                    })
                #print r.content
                return [message_list, nr_of_messages]
            else:
                return [[], 0]

    def updateMessageCache(self):
        page_nr= 1
        nr_of_messages= 1   # need a value greater 0 to start the loop
        requests= 0
        self.message_cache= []
        while nr_of_messages > 0 and requests < 50:
            message_list, nr_of_messages= self.getMessages(page_nr)
            if message_list == False or nr_of_messages == False:
                return False
                
            self.message_cache.extend(message_list)
            if nr_of_messages < self.messages_per_request: break    #this must be the last page, so stop
            page_nr+=1
            requests+=1

        print "Found {} messages in total".format(len(self.message_cache))

        # Let's concatenate splitted PGP messages (we can't do the others)
        self.message_cache.reverse()
        
        concatenate= False
        pgp_begin_index= None
        list_ids_to_delete= []
        for list_id, message in enumerate(self.message_cache[:]):
            if '-----BEGIN PGP MESSAGE-----' in message['content']:
                pgp_begin_index= list_id
                concatenate= True
                self.message_cache[list_id]['is_pgp']= True
                print 'found PGP BEGIN' + '-'*10

            elif concatenate and isinstance(pgp_begin_index, int):
                print 'concatenating...'
                self.message_cache[pgp_begin_index]['content']+= message['content']
                self.message_cache[pgp_begin_index]['indices'].append(message['indices'][0])
                list_ids_to_delete.append(list_id)

            if ('-----END PGP MESSAGE-----' in message['content'] or
               (isinstance(pgp_begin_index, int) and '-----END PGP MESSAGE-----' in self.message_cache[pgp_begin_index]['content'])):
                concatenate= False
                print 'found PGP END, stopped concatenating'
            
        for list_id in sorted(list_ids_to_delete, reverse=True): del self.message_cache[list_id]

        self.message_cache.reverse()

        if concatenate:
            #we have a problem, last message had no '-----END PGP MESSAGE-----'
            raise IncompletePGP("Couldn't find '-----END PGP MESSAGE-----', after '-----BEGIN PGP MESSAGE-----'")

        #for list_id, message in enumerate(self.message_cache):
            #print 'indices:', message['indices'], 'is_pgp:', message['is_pgp'], '\nmessage:', message['content']

       
    def getPageOfMessages(self, page_nr, messages_per_page):
        print 'Page Nr. {} with {} messages was requested.'.format(page_nr, messages_per_page)
        start= (page_nr-1)*messages_per_page
        end= page_nr*messages_per_page
        messages= self.message_cache[start:end]
        return messages, len(messages)


    def sendMessage(self, message, phone):
        url= self.api_url+"/sms/send-sms"
        post_data= self.xml_header+ """
            <request>
                <Index>-1</Index>
                <Phones><Phone>{}</Phone></Phones>
                <Sca></Sca>
                <Content>{}</Content>
                <Length>{}</Length>
                <Reserved>1</Reserved>
                <Date>{}</Date>
            </request>""".format(phone, message, len(str(message)), datetime.datetime.now().strftime('%Y-%m-%d %X'))
        try:
            r= requests.post(url, data= post_data, timeout= self.timeout)
        except requests.exceptions.Timeout:
            self.error("The request timed out while trying to connect to the remote server. It took longer than "+str(self.timeout)+" seconds.")
            return False
        except requests.exceptions.ConnectionError:
            self.error("A Connection error occurred.")
            return False
        else:
            root = ET.fromstring(r.content)
            print r.content
            if root.tag == 'error':
                self.error(self.__class__.__name__+" returned error {}.".format(root.text))
                return False
            elif root.tag == 'response' and root.text == 'OK':
                return True
            else:
                self.error(self.__class__.__name__+" returned invalid response.")
                return False

    def deleteMessage(self, index):
        url= self.api_url+"/sms/delete-sms"
        post_data= self.xml_header+ """
            <request>
                <Index>{}</Index>
            </request>""".format(index)
        try:
            r= requests.post(url, data= post_data, timeout= self.timeout)
        except requests.exceptions.Timeout:
            self.error("The request timed out while trying to connect to the remote server. It took longer than "+str(self.timeout)+" seconds.")
            return False
        except requests.exceptions.ConnectionError:
            self.error("A Connection error occurred.")
            return False
        else:
            root = ET.fromstring(r.content)
            print r.content
            if root.tag == 'error':
                self.error(self.__class__.__name__+" returned error {}.".format(root.text))
                return False
            elif root.tag == 'response' and root.text == 'OK':
                return True
            else:
                self.error(self.__class__.__name__+" returned invalid response.")
                return False


if __name__ == '__main__':
    modem= E303('192.168.1.1', 4)
    
    try:
        modem.updateMessageCache()
    except IncompletePGP:
        print 'PGP END missing.'

    print modem.getPageOfMessages(1,4)
    print modem.getPageOfMessages(2,4)
