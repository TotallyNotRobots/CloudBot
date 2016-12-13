#DWI for the fucking lUsers in my channel, by IlGnome


import random
from cloudbot import hook



DWImacros =['https://i.imgur.com/WhgY2sX.gif',
			      'https://i.imgur.com/eGInc.jpg',
			      'https://i.imgur.com/KA3XSt5.gif',
			      'https://i.imgur.com/rsuXB69.gif',
			      'https://i.imgur.com/fFXmuSS.jpg',
			      'https://j.gifs.com/L9mmYr.gif',
			      'https://i.imgur.com/nxMBqb4.gif']

#This part currently broken
DWIphrases = [	'Looks like {} needs',
				        'Ever think that {} just needs to',
			        	'Jesus fuck, {}, just',

			      	]




@hook.command('dwi','dealwithit')

def DWI(text, message):
	'''Tell some one in the channel to deal with it'''
	PersonNeedsToDeal = text.strip()

	message('\x02 {}\x02 {}'.format(PersonNeedsToDeal, random.choice(DWImacros)))
