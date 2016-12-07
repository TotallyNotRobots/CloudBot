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

@hook.command('halaal', 'halal')
def	serving(text, message):
	'''Serves halaal dishes to some one in the channel'''
	diner = text.strip()

	if diner =='':
		out = 'Has {} {} {}'.format('quantity', 'quality', 'dish')
		message(out)
	else:
		out = 'Serves {} {} {} {}'.format('diner', 'quantity', 'quality', 'dish')
		message(out)


#written by ilgnome
#find me in #gonzobot
