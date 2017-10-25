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

DWIphrases = [	
				'Stop complaining, \x02{}\x02, and',
				'Jesus fuck \x02{}\x02, just',
				'Looks like \x02{}\x02 needs to',
				'Ever think that \x02{}\x02 just needs to'
				

				]


Facepalmacros = ['https://i.imgur.com/iWKad22r.jpg',
                 'https://i.imgur.com/3Jauxrw.jpg',
                 'https://i.imgur.com/kFyKOgj.gif',
                 'https://i.imgur.com/5JaFlhU.jpg?1',
                 'https://i.imgur.com/qbnNXWy.gif',
                 'https://i.imgur.com/h46ycmx.png',
                 'https://i.imgur.com/gPNQzaf.jpg',
                 'https://i.imgur.com/9I8A9C5.jpg']


@hook.command('dwi','dealwithit')

def DWI(text, message):
	'''Tell some one in the channel to deal with it. File located in dwi.py'''
	PersonNeedsToDeal = text.strip()

	message('{} {}'.format(random.choice(DWIphrases).format(PersonNeedsToDeal), random.choice(DWImacros)))

@hook.command('fp','facepalm')

def FP(text,message):
	''' Expresses your frustration with another user. File located in dwi.py'''
	FacePalmer = text.strip()

	message('Dammit {} {}'.format(FacePalmer, random.choice(Facepalmacros)))    
