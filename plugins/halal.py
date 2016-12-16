#halaal for gonzobot
import random
from cloudbot import hook


quantity = ['a little bit of',
			'a heaping pile of',
			'a moderate serving of',
			'a taste of',
			'just a smell of',
			]


quality = [	'fresh made',
			'left over',
			'just out of the oven'

			]

dish = 	[	'Rice and Goat Meat',
			'Goat Curry',
			'Hummus bi Tahina',
			'Läghmän',
			'Mutton biryani',
			'Kabuli palao',
			'Shakshouka',
			'Mutton Msala',
			'Fatteh Betnjan',
			'Caprese stuffed chicken breast',
			'Maqloobeh',
			'Koofteh berenji',
			'Fish Makkanwala',
			'Szechwan'
			]

@hook.command('halaal', 'halal', autohelp = False)
def	serving(text, action):
	'''Serves halaal dishes to some one in the channel'''
	diner = text.strip()

	if diner =='':
		action('Has {} {} {}'.format(random.choice(quantity), random.choice(quality), random.choice(dish)))

	else:
		action('Serves {} {} {} {}'.format(diner, random.choice(quantity), random.choice(quality), random.choice(dish)))


#written by ilgnome
#find me in #gonzobot
