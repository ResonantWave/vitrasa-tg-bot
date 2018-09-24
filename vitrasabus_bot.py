#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import requests
import MySQLdb
import time
import os
import logging

import telebot

from xml.etree import ElementTree
from suds import WebFault
from suds.client import Client
from telebot import types

db = MySQLdb.connect(host = 'localhost', user = 'root', db = 'vitrasa', charset = 'utf8')
cur = db.cursor()
logger = telebot.logger
bus_bot = telebot.TeleBot('')

telebot.logger.setLevel(logging.DEBUG)

time_ignore = 5 * 60

def get_nearest(latitude, longitude):
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
    WSDL_URL = 'http://sira.intecoingenieria.com/SWEstimacionParada.asmx?WSDL'
    client = Client(url=WSDL_URL)

    factory = client.factory.create('tns:EstimacionParadaIdParada')
    factory.IdParada = stop
    try:
        response = client.service.EstimacionParadaIdParada(factory)
    except WebFault:
        return '\nNo hay buses disponibles para mostrar en este momento en esta parada\n'

    response_encoded = response.encode('utf-8')
    tag_newdataset = ElementTree.fromstring(response_encoded)

    query = ('SELECT name FROM `stops` WHERE id = %(id)s') # get the stop name
    cur.execute(query, {'id': stop})

    output = "Próximos buses en <b>" + cur.fetchone()[0].encode('utf-8') + '</b> (' + str(stop) + ')\n\n'
    if len(tag_newdataset) == 0:
        output += '\nNo hay buses disponibles para mostrar en este momento en esta parada\n'
    else:
        for i in tag_newdataset:
            output += 'Línea <b>' + i.find('Linea').text + '</b>: ' + i.find('minutos').text + ' minutos\n'
    return output

@bus_bot.message_handler(commands=['start'])
def handle_start_help(m):
    if (int(time.time()) - time_ignore) > m.date:
        return

    bus_bot.send_chat_action(m.chat.id, 'typing')
    markup = types.ReplyKeyboardMarkup()
    itembtn1 = types.KeyboardButton('/parada')
    markup.row(itembtn1)

    bus_bot.send_message(m.chat.id, 'Por favor, elige una acción. Para cualquier sugerencia o error, por favor contacta con 644 444 326', reply_markup = markup)

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
            query = ('SELECT id, name FROM `stops` WHERE name LIKE %(name)s LIMIT 15')
            cur.execute(query, {'name': '%' + '%'.join(a[1:len(a)]) + '%'})
            if cur.rowcount == 0:
                output = 'No se han encontrado paradas con ese nombre'
            elif cur.rowcount == 1:
                output = get_bus(cur.fetchone()[0])
            else:
                output = 'Varias paradas encontradas:\n\n'
                for(id, name) in cur:
                    output += 'ID: <b>' + str(id) + '</b>; <b>' + name + '</b>\n'
    else:
        output = 'Error de argumento. Uso: /parada <i>parada</i> (Por ejemplo, <i>/parada praza españa</i>).\nTambién puedes enviar tu ubicación para ver una lista de paradas más cercanas.'

    bus_bot.send_message(m.chat.id, output, parse_mode='HTML')

@bus_bot.message_handler(content_types=['location'])
def handle_location(m):
    bus_bot.send_message(m.chat.id, get_nearest(m.location.latitude, m.location.longitude), parse_mode='HTML')

while True:
    bus_bot.polling(none_stop = True)
