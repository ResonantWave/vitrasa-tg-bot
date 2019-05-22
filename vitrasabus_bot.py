#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import requests
import MySQLdb
import time
import os
import logging
import sys

import telebot

from xml.etree   import ElementTree
from suds        import WebFault
from suds.client import Client
from telebot     import types
from urllib2     import urlopen

reload(sys)
sys.setdefaultencoding("utf-8")

db = MySQLdb.connect(host = 'localhost', user = 'root', db = 'vitrasa', charset = 'utf8')
cur = db.cursor()
logger = telebot.logger
bus_bot = telebot.TeleBot('')

telebot.logger.setLevel(logging.DEBUG)

time_ignore = 5 * 60

def createUser(tg_id):
    query = 'INSERT INTO `userConfig` (tg_id, fav0, fav1, fav2, fav3) VALUES (%(tg_id)s, NULL, NULL, NULL, NULL);'
	
    data = {'tg_id': str(tg_id)}

    cur = db.cursor()
    cur.execute(query, data)
    db.commit()
    cur.close()



def getUserData(tg_id):
    """
    Fetches user data from database. If no data was previously stored, a new user entry will be created.
    Returns a list of the four saved favourites; with <vacio> representing empty favourite.
    """
    query = 'SELECT * FROM `userConfig` WHERE tg_id = %(user_id)s'
    data = {'user_id': str(tg_id)}

    cur = db.cursor()
    cur.execute(query, data)

    empty_string = '<vacio>'
    # if user doesn't exists on db, create and return empty fav list
    if(cur.rowcount == 0):
        createUser(tg_id)
        return [empty_string, empty_string, empty_string, empty_string]

    (_, fav0, fav1, fav2, fav3) = cur.fetchone()

    # if any of the columns is None, then we return <vacio>. Else, whatever text is in the db.
    fav0 = fav0 if str(fav0) != 'None' else empty_string
    fav1 = fav1 if str(fav1) != 'None' else empty_string
    fav2 = fav2 if str(fav2) != 'None' else empty_string
    fav3 = fav3 if str(fav3) != 'None' else empty_string

    return [fav0, fav1, fav2, fav3]

def get_nearest(latitude, longitude):
    """
    From given point (latitude, longitude), looks for the nearest stops in the db.
    
    If no entries are found, an appropriate message will be returned.
    If just one entry is found, it will be directly queried.
    If more than one entry is found, a list of the first 15 will be shown.
    """
    # harvesine formula, calculate great sphere distance between two locations
    query = """SELECT id, name, (
               6371000
               * acos(cos(radians(%(lat)s))
                  * cos(radians(lat))
                  * cos(radians(lon)
                  - radians(%(lon)s))
                  + sin(radians(%(lat)s))
                  * sin(radians(lat))
                )
               ) AS distance FROM `stops` ORDER BY distance LIMIT 15;
            """

    data = {'lat': latitude, 'lon': longitude}
    cur.execute(query, data)
    if cur.rowcount == 0:
        return 'No se han encontrado paradas cercanas'
    elif cur.rowcount == 1:
        return get_bus(cur.fetchone()[0])
    else:
        output = 'Paradas más cercanas encontradas:\n\n'
        for(id, name, distance) in cur:
            output += 'ID: <b>' + str(id) + '</b>; <b>' + name.encode('utf-8') + '</b> (' + str(int(distance)) + ' metros)\n'
        return output

def get_bus(stop):
    """
    Downloads and shows real-time bus data in the specified stop id.
    
    If no buses are expected to come, an appropriate message will be shown.
    Else, a list of all next buses with ETAs will be shown.
    """
    WSDL_URL = 'http://sira.intecoingenieria.com/SWEstimacionParada.asmx?WSDL'
    client = Client(url = WSDL_URL)

    factory = client.factory.create('tns:EstimacionParadaIdParada')
    factory.IdParada = stop
    try:
        response = client.service.EstimacionParadaIdParada(factory)
    except WebFault: # sometimes, for unknown reasons, the request fails epicly. Catch it and just return nothing.
        return '\nNo hay buses disponibles para mostrar en este momento en esta parada\n'

    response_encoded = response.encode('utf-8')
    tag_newdataset = ElementTree.fromstring(response_encoded)

    # because we use the stop id and not the name, we need to get it now to show it to the user
    query = ('SELECT name FROM `stops` WHERE id = %(id)s') # get the stop name
    cur.execute(query, {'id': stop})

    output = 'Próximos buses en <b>' + cur.fetchone()[0].encode('utf-8') + '</b> (' + str(stop) + ')\n\n'
    if len(tag_newdataset) == 0:
        output += '\nNo hay buses disponibles para mostrar en este momento en esta parada\n'
    else:
        for i in tag_newdataset:
            output += 'Línea <b>' + i.find('Linea').text + '</b>: ' + i.find('minutos').text + ' minutos\n'
    return output

def get_stop_id(a):
    # _a_ should be a list containing all query terms. Eg ['praza', 'de', 'españa']
    query = ('SELECT id, name FROM `stops` WHERE name LIKE %(name)s LIMIT 15')
    cur.execute(query, {'name': '%' + '%'.join(a) + '%'})
    if cur.rowcount == 0:
        if a[0] == '<vacio>':
            output = 'Debes configurar esta parada favorita con /configurarfavoritos'
        else:
            output = 'No se han encontrado paradas con ese nombre'
    elif cur.rowcount == 1:
        output = get_bus(cur.fetchone()[0])
    else:
        output = 'Varias paradas encontradas:\n\n'
        for(id, name) in cur:
            output += 'ID: <b>' + str(id) + '</b>; <b>' + name + '</b>\n'
    return output

def getFavKbd(chat_id, prefix_index = False):
    """
    Constructs and returns a four-button keyboard for favourite handling.
    
    When editing favourites prefix_index is set to True, so when any of them is clicked we know which favourite to edit.
    """
    (fav0, fav1, fav2, fav3) = getUserData(chat_id)
    markup = types.ReplyKeyboardMarkup(one_time_keyboard = True)
    button_fav0 = types.KeyboardButton(('0: ' if prefix_index else '') + str(fav0))
    button_fav1 = types.KeyboardButton(('1: ' if prefix_index else '') + str(fav1))
    button_fav2 = types.KeyboardButton(('2: ' if prefix_index else '') + str(fav2))
    button_fav3 = types.KeyboardButton(('3: ' if prefix_index else '') + str(fav3))
    markup.row(button_fav0, button_fav1)
    markup.row(button_fav2, button_fav3)
    return markup

# main commands #########

@bus_bot.message_handler(commands=['start'])
def handle_start_help(m):
    if (int(time.time()) - time_ignore) > m.date:
        return

    markup = types.ReplyKeyboardMarkup()
    button_parada = types.KeyboardButton('/parada')
    button_favoritos = types.KeyboardButton('/favoritos')
    markup.row(button_parada, button_favoritos)

    bus_bot.send_message(m.chat.id, 'Por favor, elige un comando.', reply_markup = markup)

@bus_bot.message_handler(commands=['parada'])
def get_id(m):
    if (int(time.time()) - time_ignore) > m.date:
        return

    a = m.text.lower().split()
    output = ''
    if len(a) > 1:
        if a[1].isdigit():
            output = get_bus(a[1])
        else:
            output = get_stop_id(a[1:len(a)])
    else:
        output = 'Error. Uso: /parada <i>parada</i> (Por ejemplo, <i>/parada praza españa</i>).\nTambién puedes enviar tu ubicación para ver una lista de paradas más cercanas.'

    bus_bot.send_message(m.chat.id, output, parse_mode='HTML')

# favourite handling #########

@bus_bot.message_handler(commands=['favoritos'])
def favHandler(m):
    if (int(time.time()) - time_ignore) > m.date:
        return

    msg = bus_bot.send_message(m.chat.id, 'Elige una parada favorita', reply_markup = getFavKbd(m.chat.id))
    bus_bot.register_next_step_handler(msg, getFav)

def getFav(m):
    """
    Handles favourites. If the clicked favourite is just a number, it will be directly queried. 
    If it's a name, its stop ID will be looked for in the db.
    """
    if m.text.isdigit():
        # gets stop directly by stop id
        output = get_bus(m.text)
    else:
        # gets stop by first getting its id from db
        output = get_stop_id(m.text.split(' '))
    bus_bot.send_message(m.chat.id, output, parse_mode = 'HTML', reply_markup = types.ReplyKeyboardRemove(selective = False))



@bus_bot.message_handler(commands=['configurarfavoritos'])
def setFavHandler(m):
    if (int(time.time()) - time_ignore) > m.date:
        return
    msg = bus_bot.send_message(m.chat.id, 'Elige un favorito para modificar', reply_markup = getFavKbd(m.chat.id, True))
    bus_bot.register_next_step_handler(msg, setFavInput)
    
def setFavInput(m):
    global oldStop
    oldStop = m.text
    msg = bus_bot.send_message(m.chat.id, '¿Por qué parada quieres cambiar este favorito? Escribe el número o nombre de la parada')
    bus_bot.register_next_step_handler(msg, setFavFinal)

def setFavFinal(m):
    global oldStop
    allowed_inputs = ['0', '1', '2', '3']

    if oldStop.split(':')[0] in allowed_inputs:
        query = 'UPDATE `userConfig` SET fav{} = %(new_fav)s WHERE tg_id = %(tg_id)s'.format(oldStop.split(':')[0]) # i dont like this
	
        data = {'tg_id': str(m.chat.id), 'new_fav': m.text}

        cur = db.cursor()
        cur.execute(query, data)
        db.commit()
        cur.close()
        output = 'Favorito actualizado! Ya puedes acceder a él con /favoritos'
    else:
        output = 'Ha ocurrido un error al configurar el favorito. Inténtalo de nuevo con /configurarfavoritos'
    bus_bot.send_message(m.chat.id, output)

# misc commands #########

@bus_bot.message_handler(content_types=['location'])
def handle_location(m):
    bus_bot.send_message(m.chat.id, get_nearest(m.location.latitude, m.location.longitude), parse_mode='HTML')

@bus_bot.message_handler(commands=['cambios'])
def changelog(m):
    output = 'Versión <b>1.2</b>\n'
    output += '¿Qué ha cambiado?\n\n'
    output += ' - Paradas favoritas ⭐ (/favoritos y /configurarfavoritos)\n'
    output += ' - Más rapidez de búsqueda de paradas\n'
    output += ' - Añadidos <b>9 millones</b> de lámparas LED 💡\n'
    bus_bot.send_message(m.chat.id, output, parse_mode = 'HTML')

# main loop #########

while True:
    bus_bot.polling(none_stop = True)
