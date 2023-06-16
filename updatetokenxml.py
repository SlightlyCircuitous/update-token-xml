#!/usr/bin/env python3

"""
v3.2 - Handle subtype logic with Try/Except instead of has_subtype
Command line tool to compare a new set of tokens from Scryfall with an existing token XML. Pulls down a token set from Scryfall, appends reprinted tokens to a copy of the current XML file, and creates entries for new tokens in a separate XML file. Pulls the current large Scryfall hard link for picURLs.

Does not handle:
--Filling out related or reverse-related fields
--Adding spaces to non-uniquely named tokens

Treats tokens with new reminder text as new tokens.

Run using 'python filename setcode /path/to/current/XML/file' or make the file executable with chmod and use './filename setcode /path/to/current/XML/file', when in the same folder as this script file.
"""

import requests
import sys
import time
from lxml import etree

#initialize global constants
SHORT_TAG_LIST = ['Emblem','Dungeon','Card','Token'] #Scryfall doesn't use 'State', 'Counter', or 'Companion' types; they are all rolled into 'Card'

#helper functions
def pullScryfallAPI(download_url):
    """
    Makes a request to the Scryfall API with the given download URL and outputs cards as a list of dicts
    Depends on requests and time libraries
    
    This function is adapted from Cockatrice: Magic-Spoiler download_scryfall_set(), licensed under GPL v3.0
    Copyright (C) 2022  SlightlyCircuitous

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>
    """
    
    page = 1
    token_list = []

    while download_url:
    
        cards = requests.get(download_url).json()
        if cards["object"] == "error":
            print(f"Error occurred downloading page {page}")
            break
        
        for card in cards["data"]:
            token_list.append(card)
        
        if not cards.get('has_more'): #get returns None if the key does not exist and None has a truth-value of False (though it isn't actually the boolean False)
            break
        
        download_url = cards["next_page"]
    
        page += 1
    
        time.sleep(0.5) #rate limit to keep the API gods happy
        
    return token_list

def fetchTokenInfo(sf_entry):
    """
    Pulls token information from a Scryfall entry to compare against information from the Cockatrice token XML.
    Also takes the large image uri for use in creating set lines and new token entries.
    
    :param sf_entry: a dictionary containing token information from Scryfall; either a full entry 
                        or part of a double-faced token entry
                        
    :return match_info: a dictionary containing only the relevent information needed from the full scryfall entry
    """
    
    match_info = {}
    
    match_info['token_name'] = sf_entry['name'] #using token name from Scryfall as written; some names need 'token' appended or spaces added on the end
    match_info['token_text'] = sf_entry['oracle_text']
    match_info['token_type'] = sf_entry['type_line']
    match_info['token_colors'] = sorted(sf_entry['colors'])
        
    if 'power' in sf_entry.keys() and 'toughness' in sf_entry.keys():
            match_info['token_pt'] = sf_entry['power']+'/'+sf_entry['toughness']

    else:
        match_info['token_pt'] = ""
        
    match_info['token_image'] = sf_entry['image_uris']['large']
        
    return match_info


def xmlMatch(xml_root, token_info, set_code):
    """
    Compares a given token to the current XML file and and inserts a new set line into an existing entry 
    if one is found. Updates global variable reprint_count to reflect if a match was found or not.
    Depends on lxml library.
    
    :param xml_root: the root of the XML file that new tokens are compared against
    :param token_info: a dict containing relevent information on the new token being compared
    :set_code: the set code for the new set
    
    :return match_found: a boolean indicating whether or not a match to an exisiting token was found
    """
    
    global reprint_count
    
    match_found = False
    
    for xml_card in xml_root.findall('./cards/'):
                    
        #unify formatting between scryfall and the token xml for matching
            
        #name
        xml_name = xml_card.findtext('name')
            
        #text
        if etree.iselement(xml_card.find('text')):
            xml_text =  xml_card.findtext('text')

        else:
            xml_text = ""

        #colors
        if etree.iselement(xml_card.find('./prop/colors')):
            xml_colors = sorted(list(xml_card.findtext('./prop/colors'))) #need to make it a list to sort it
        else:
            xml_colors = []

        #power and toughness   
        if etree.iselement(xml_card.find('./prop/pt')):
            xml_pt = xml_card.findtext('./prop/pt')

        else:
            xml_pt = ""

        #append picURL/set line to existing file if a perfect match
        if (xml_name.startswith(token_info['token_name'])) and (xml_text == token_info['token_text']) and (xml_card.find('./prop/type').text == token_info['token_type']) and (xml_colors == token_info['token_colors']) and (xml_pt == token_info['token_pt']):

            new = etree.Element('set',attrib = {'picURL':token_info['token_image']})
            new.text = set_code.upper()

            #insert needs a relative index; <text> may or may not exist
            if etree.iselement(xml_card.find('./text')):
                xml_card.insert(3,new)
                
            else:
                xml_card.insert(2,new)
                
            match_found = True
            reprint_count += 1   
            
    return match_found
                        
def createXmlEntry(token_info, set_code):
    """
    Creates a new XML entry based on the token information in token_info and the given set_code.
    Depends on lxml library.
    
    :param token_info: a dict containing relevent information on the new token being compared
    :set_code: the set code for the new set
    
    :return card: an lxml Element object containing all the necessary information for a new XML entry
    """

    card = etree.Element('card')

    name = etree.SubElement(card,'name')
    name.text = token_info['token_name']

    if token_info['token_text'] != "":
        text = etree.SubElement(card, 'text')
        text.text = token_info['token_text']

    prop = etree.SubElement(card,'prop')

    if token_info['token_colors'] != []:
        colors = etree.SubElement(prop,'colors')
        colors.text = "".join(token_info['token_colors']) #put colors back into a string

    card_type = etree.SubElement(prop,'type')
    card_type.text = token_info['token_type']

    maintype = etree.SubElement(prop,'maintype')
       
    #determine the maintype and whether or not the token has a subtype   
    if 'Emblem' in card_type.text:
        maintype.text = "Emblem"
    
    elif 'Dungeon' in card_type.text:
        maintype.text = "Dungeon"
        
    #creature is the maintype for any type line with the word 'Creature' in it
    elif 'Creature' in card_type.text:
        maintype.text = 'Creature'

    #it is important to do Artifact and Enchantment after Creature since it supersedes them in maintype
    elif 'Artifact' in card_type.text:
        maintype.text = 'Artifact'
        
    elif 'Enchantment' in card_type.text:
        maintype.text = 'Enchantment'
        
    #in case of weird types like 'card' or 'token' that Scryfall likes to use    
    else:
        maintype.text = 'Please edit manually'
        print (f"Could not determine maintype for {name.text}. Please edit manually")

    try: 
        
        #anything after the emdash should be the subtype, but not all cards have an emdash
        subtype = card_type.text.split(' — ')[1]

        #if the subtype matches the name of the token, it's a generic token
        if subtype == token_info['token_name']:
            name.text+=' Token'
            
    except IndexError:
        
        #anything without an emdash is basically guarenteed not to need 'Token' appended
        pass
    
    #the current convention is to have a cmc line of 0 for creatures and artifacts but not anything else
    if token_info['token_type'] not in SHORT_TAG_LIST:
        cmc = etree.SubElement(prop,'cmc')
        cmc.text = '0'

    if token_info['token_pt'] != "":
        pt = etree.SubElement(prop,'pt')
        pt.text = token_info['token_pt']

    card_set = etree.SubElement(card, 'set', attrib={'picURL':""})
    card_set.set('picURL', token_info['token_image'])
    card_set.text = set_code.upper()
    
    #add 'related' element if the card transforms into something
    if 'transform' in token_info['token_text'] or 'Transform' in token_info['token_text']:
        related = etree.SubElement(card, 'related')
        related.text = "" #prevents short tag

    reverse_related = etree.SubElement(card, 'reverse-related')
    reverse_related.text = "" #prevents short tag
    
    token = etree.SubElement(card,'token')
    token.text = '1'

    tablerow = etree.SubElement(card,'tablerow')
    if maintype.text == 'Creature':
        tablerow.text = '2'
    else:
        tablerow.text = '1'
            
    return card
    
#main function
def updateTokenXML(set_code, xml_file):
    """
    Builds two xmls of tokens based on a scryfall API search. Puts reprints in xml_file and new tokens 
    in a new xml_file. Does not handle reverse-related. Depends on re and lxml libraries. 
    
    :param set_code: the three letter code representing the set
    :param xml_file: the xml list of tokens to check new ones against
    """
    
    #pull down the token set from Scryfall using pull_scryfall_API()
    token_set = pullScryfallAPI('https://api.scryfall.com/cards/search?q=s%3A'+'t'+set_code.lower())
    
    #parse the existing token xml
    parser = etree.XMLParser(remove_blank_text=True) #removes blank spaces to make pretty print behave with .insert
    xml_tree = etree.parse(xml_file,parser)
    xml_root = xml_tree.getroot()
    
    #create new xml tree to add new tokens to
    new_root = etree.Element('newtokens')
    cards = etree.SubElement(new_root,'cards') 
    
    #declare globals
    global reprint_count

    #initialize counters for this function
    new_token_count  = 0
    double_faced_count = 0
    reprint_count = 0
    
    for sf_token in token_set:
        
        #handle double-faced tokens specially due to their unique file structure
        if sf_token['layout'] == 'double_faced_token':
            
            double_faced_count += 1
            
            for sf_face in sf_token['card_faces']:

                #get all the relevent information out of the face entry to avoid passing the whole thing
                face_info = fetchTokenInfo(sf_face)

                #look for a match in the XML and insert a set line if found
                match_found = xmlMatch(xml_root, face_info, set_code)

                #create a full entry for new token and add it to a new XML file if no match
                if not match_found:
                    cards.append(createXmlEntry(face_info, set_code))
                    new_token_count+=1
        
        #handle everything else        
        else:
            
            #get all the relevant information out of the Scryfall entry to avoid passing the whole thing
            token_info = fetchTokenInfo(sf_token)
            
            #look for a match in the XML and insert a set line if found
            match_found = xmlMatch(xml_root, token_info, set_code)
                
            #create a full entry for new token and add it to a new XML file if no match
            if not match_found: 
                cards.append(createXmlEntry(token_info, set_code))
                new_token_count+=1
                    
    #create and output xml file -- contains new tokens
    new_tree = etree.ElementTree(new_root)
    etree.indent(new_tree,space='    ') #pretty print defaults to two spaces apparently
    new_tree.write(f'{set_code}_new_tokens.xml', encoding='utf-8', pretty_print=True)
    
    #outputs the amended token xml file -- contains reprinted tokens
    etree.indent(xml_tree,space='    ')
    xml_tree.write(f'token_file_{set_code}_update.xml',encoding='utf-8', xml_declaration=True, pretty_print=True)
    
    #output some token facts
    print(f'Created {new_token_count} new token entries in {set_code}_new_tokens.xml')
    print(f'Appended set lines for {reprint_count} reprinted tokens in token_file_{set_code}_update')
    print(f'Please check entries for accuracy, fill in related and reverse-related elements,\nand add spaces after non-unique token names as necessary.')
    
#actually run the program
updateTokenXML(sys.argv[1],sys.argv[2])
