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
kdish = ['gefilte fish',
         'matzo ball soup',
         'cholent',
         'sufganiyot',
         'cream cheese with lox bagel',
         'lamb merguez with lentils and pears',
         'warm apple streusel with ice cream on top',
         'mushroom and truffle pizza',
         'lemon and rosemary salad with a side of rice',
         'latkes with applesauce',
         'challah french toast',
         'grilled fish tacos with chili-lime dressing',
         'date charoset',
         'huevos haminados',
         'baba-ghanouj',
         'bastani with freshly baked pita',
         'hummus with perfectly fried falafel',
         'mujadrah with warm bread',
         'shishlik with red peppers, mushrooms, and onion',
         'spicy shakshouka with french bread',
         'hadgi badah with a tall glass of apple juice',
         'malawah with a large glass of milk',
         'sweet kugel with extra sugar on top',
         'hamantaschen with date and raspberry filling',
         'marbled halva with almonds on top',
         'labna with a side of chili sauce',
         'polow shirin with extra pomegranate',
         'lamb bademjan'
         'beef kubbeh with extra chili peppers',
         'beef shawarma with a side of hummus and rice',
         'lamb and mushroom kofta with a large coke',
         'cheese and spinach sambousek',
         'bamieh with a side of grilled chicken',
         'chicken tagine with saffron rice and a slice of lechuch',
         'kofta mishmisheya with grilled vegetables',
         'charoset with day old matzah',
         'sour cherry rugelach',
         'orange-scented flan with dulce de leche syrup',
         'brisket with potatoes and a spinach salad',
         'bouikos con kashkaval',
         'lemon-rice soup with soda crackers'
         ]



@hook.command('halaal', 'halal', autohelp = False)
def	serving(text, action):
	'''Serves halaal dishes to some one in the channel'''
	diner = text.strip()

	if diner =='':
		action('has {} {} {}'.format(random.choice(quantity), random.choice(quality), random.choice(dish)))

	else:
		action('Serves {} {} {} {}'.format(diner, random.choice(quantity), random.choice(quality), random.choice(dish)))

@hook.command('kosher', autohelp=False)
def kserving(text, action):

    '''Servers a Kosher dish to some one in the channel. Part of halal.py. Made with help of snoonet user Yat'''
    kdiner = text.strip()
    if kdiner =='':
    	action('has {} {} {}'.format(random.choice(quantity), random.choice(quality), random.choice(kdish)))
    else:
    	action('Serves {} {} {} {}'.format(kdiner, random.choice(quantity), random.choice(quality), random.choice(kdish)))

#written by ilgnome
#find me in #gonzobot
