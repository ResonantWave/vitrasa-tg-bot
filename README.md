**Update: This bot no longer works, as the bus stops API is no longer available**
# Vitrasa Telegram bot
Real-time data from Vigo buses, in a Telegram bot

There's just one command, `/parada`, which accepts a stop ID or name as an argument. Examples:

`/parada 2310`
`/parada praza españa`
`/parada urzaiz`

If more than a stop is found, a disambiguation message will be shown.

Also, if location is sent, a list of the nearest stops will be returned (15 stops max)

### Required libraries

* [telebot](https://github.com/eternnoir/pyTelegramBotAPI)

### Usage notes

Replace the Telegram bot key in [vitrasabus_bot.py](vitrasabus_bot.py)

For the location functionality, the use of MySQL or MariaDB is required. Table structure and data are available [here](table.sql).

### Contributors
 *  [@ResonantWave](https://github.com/ResonantWave)

### Contributing
 *  The code is licensed under the [GPL v3.0](LICENSE)
 *  Feel free to contribute to the code

