import ConfigParser
import redis
import gammu
import json
import logging
from logging import Formatter
from logging.handlers import RotatingFileHandler
import traceback
import sys
import time


logger = logging.getLogger()

def readConfig(filename='config.ini'):
    try:
        conf = ConfigParser.ConfigParser()
        conf.read('config.ini')

        config = dict()
        # read config
        config['HOST'] = conf.get('redis', 'host')
        config['PORT'] = conf.getint('redis', 'port')
        config['DB'] = conf.getint('redis', 'db')
        config['PASSWORD'] = conf.get('redis', 'password')
        config['KEY'] = conf.get('redis', 'key')

        config['GAMMU_CONFIG'] = conf.get('gammu', 'config_file')

        config['LOGGING_FILE'] = conf.get('logging', 'filename')
        config['LOGGING_LEVEL'] = conf.get('logging', 'level')
    except:
        logger.error(traceback.format_exc())

    return config

def connectRedis(config):
    try:
        queue = redis.StrictRedis(host=config['HOST'], port=config['PORT'],
            db=config['DB'], password=config['PASSWORD'])
    except:
        logger.error(traceback.format_exc())
    return queue

def connectGammu(config):
    try:
        phone = gammu.StateMachine()
        phone.ReadConfig(Filename=config['GAMMU_CONFIG'])

        logger.info('Connecting to phone...')
        phone.Init()
    except gammu.ERR_DEVICENOTEXIST, gammu.ERR_DEVICEOPENERROR:
        logger.error('No Phone connected!')
        logger.warning('Exiting...')
        sys.exit(1)
    except:
        logger.error(traceback.format_exc())
        logger.warning('Exiting...')
        sys.exit(1)
        
    logger.info('Phone connected!')
    return phone

def sendSMSLoop(config):
    queue = connectRedis(config)
    phone = connectGammu(config)
    while True:
        try:
            entry = json.loads(queue.blpop(config['KEY'])[1])
            message = dict(Text=entry['Text'], Number=entry['Number'],
                    SMSC=dict(Location=1))
        except:
            logger.error(traceback.format_exc())

        try:
            phone.SendSMS(message)
            logger.info('SMS sent to %s: %s' % (entry['Number'],
                entry['Text']))
        except gammu.ERR_EMPTYSMSC, gammu.ERR_GETTING_SMSC:
            logger.error('SMSC does not exist. Probably the phone is \
disconnected')
            logger.warning('Exiting...')
            sys.exit(1)
        except gammu.ERR_NOTCONNECTED:
            logger.error('Phone Not Connected!')
            logger.warning('Exiting...')
            sys.exit(1)
        except:
            logger.error(traceback.format_exc())
            logger.warning('Exiting...')
            sys.exit(1)


def quit(signum, frame):
    logger.warning('Exiting...')
    sys.exit(0)
            
if __name__ == '__main__':
    config = readConfig(filename='config.ini')
    file_handler = RotatingFileHandler(filename=config['LOGGING_FILE'],
            maxBytes=1048576, backupCount=10)
    file_handler.setFormatter(Formatter(
        '%(asctime)s %(levelname)s: %(message)s '
        '[in %(pathname)s:%(lineno)d]'
        ))
    logger.addHandler(file_handler)
    logger.setLevel(getattr(logging, config['LOGGING_LEVEL']))

    logger.info('SMS Send Started')

    import signal

    signal.signal(signal.SIGQUIT, quit)

    sendSMSLoop(config)
