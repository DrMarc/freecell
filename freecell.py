# Copyright (C) 2021 Marc Schönwiesner <marcs@uni-leipzig.de>
# straight translation as an exercise in curses programming
# from the C implementation by Linus Akesson, which is
# copyright (C) 2007 Linus Akesson <linus@linusakesson.net>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import curses
import random
import copy
import argparse
import time
from collections import namedtuple

RELEASE = '1.0'

parser = argparse.ArgumentParser(description="Python implementation of the Freecell card game.")
parser.add_argument('-s', '--suits', type=str, default='shcd', help="Configures four characters as suite symbols, for instance lhes for German suit names.")
parser.add_argument('game', type=int, nargs='?', default=0, help="Integer game number. Microsoft 32,000 game numbers work.")
args = parser.parse_args()
# We now have args.suits and args.game
if args.game:
	seed = args.game
else:
	seed = random.randint(0, 2**32) # many many different games
suitesymbols = args.suits

window = None # will hold the curses window handle so that it is available in all classes

nmoves = 0
nundos = 0
work = [None] * 4 # list of 4 cards
pile = [None] * 4 # list of 4 cards
columns = [[] for i in range(8)] # list[8] of list of cards
arg = 0
face = 0
selected = False
wselected = False
selcol = 0
seln = 0
# datatype for saving past game states: list of undo tuples (column, work, pile)
undo = namedtuple('Undo', ['columns', 'work', 'pile'])
history = []

class Card:
	'''
	Class for cards with values and suits (kind).
	A card can print itself in color and determine it has a possible move
	'''
	def __init__(self, value, kind):
		self.value = value
		self.kind = kind

	def __str__(self):
		return f'{self.value:2}{suitesymbols[self.kind]}'

	def show(self, selected):
		if (self.kind % 2): # if odd
			if selected:
				window.attrset(curses.color_pair(3))
			else:
				window.attrset(curses.color_pair(1))
		else:
			if selected:
				window.attrset(curses.color_pair(2))
		window.addstr(str(self))
		window.attrset(curses.A_NORMAL)

	def mayautomove(self):
		if pile[self.kind]:
			if self.value != pile[self.kind].value + 1:
				return False
		else:
			if self.value != 1:
				return False
		# ok, card may legally be moved to the foundation, but it's only prudent if
		v = self.value
		ov1 = pile[self.kind^1].value if pile[self.kind^1] else 0 # bit-OR to select other suits
		ov2 = pile[self.kind^3].value if pile[self.kind^3] else 0
		sv = pile[self.kind^2].value if pile[self.kind^2] else 0
		# a. the values of the foundations of the different colours are at least v - 1
		if (ov1 >= v-1) and (ov2 >= v-1):
			return True
		# b. the values of the foundations of the different colours are at
		# least v - 2, and the value of the foundation of similar colour is at least v - 3
		if (ov1 >= v-2) and (ov2 >= v-2) and (sv >= v-3):
			return True
		return False

def automove():
	'''
	Move cards automatically to the correct foundation pile.
	'''
	global pile, work, columns
	for i in range(4): # check work pile for movable cards
		card = work[i]
		if card:
			if card.mayautomove():
				pile[card.kind] = card
				work[i] = None # remove from work pile
				return True # we have moved something!

	for column in columns: # check columns for movable cards
		if len(column): # if column not empty
			card = column[-1] # last card
			if card.mayautomove():
				pile[card.kind] = card
				column.pop()
				return True # we have moved something!
	return 0 # nothing to move!

def dealgame(seed):
	'''
	Deals a pseudorandom game, dependent on seed (compatible with game numbers from Microsoft Freecell).
	'''
	cardsleft = 52
	suitemap = [2, 3, 1, 0]
	holdseed = seed
	deck = list(range(52))
	for i in range(52):
		# Pick a card
		holdseed = (holdseed * 214013 + 2531011) & 0xffffffff
		c = ((holdseed >> 16) & 0x7fff) % cardsleft
		# Place it on the table.
		value = deck[c] // 4 + 1
		kind = suitemap[deck[c] % 4]
		columns[i % 8].append(Card(value=value, kind=kind))
		# Move the last card in the deck into the vacant position.
		deck[c] = deck[cardsleft - 1]
		cardsleft -= 1
	return columns

def pushundo():
	global history, nmoves
	history.append(undo(copy.deepcopy(columns), work.copy(), pile.copy()))
	nmoves += 1

def popundo():
	global columns, work, pile, nmoves, nundos, selected, wselected, arg
	if history:
		previous = history.pop()
		columns = previous.columns
		work = previous.work
		pile = previous.pile
		nmoves -= 1
		nundos += 1
	selected = False
	wselected = False
	arg = 0

def gameover():
	for card in pile:
		if not card:
			return False
		if card.value != 13:
			return False
	return True

def gameover_animation():
	mesg = 'WELL DONE!'
	window.attrset(curses.A_BOLD | curses.color_pair(4))
	window.addstr(3, 17, mesg)
	window.move(5, 43)
	window.refresh()
	time.sleep(0.05)
	for i, letter in enumerate(mesg):
		window.attrset(curses.A_BOLD | curses.color_pair(4))
		if i:
			window.addstr(3, 17 + i - 1, mesg[i - 1])
		window.attrset(curses.A_BOLD)
		window.addstr(3, 17 + i, letter)
		window.move(5, 43)
		window.refresh()
		time.sleep(0.2)
	window.attrset(curses.A_BOLD | curses.color_pair(4))
	window.addstr(3, 17, mesg)
	window.move(5, 43)
	window.refresh()

def helpscreen():
	window.erase()
	window.addstr(0, 0, "freecell " + RELEASE)
	window.addstr(0, 24, "www.linusakesson.net")
	window.addstr(2, 0, " The aim of the game is to move all cards to")
	window.addstr(3, 0, "the foundations in the upper right corner.")
	window.addstr(4, 0, " You may only move one card at a time.   The")
	window.addstr(5, 0, "foundations accept cards of increasing value")
	window.addstr(6, 0, "within each suite   (you may place 2; on top")
	window.addstr(7, 0, "of 1;).  The columns accept cards of falling")
	window.addstr(8, 0, "value, different colour (you may place 2; on")
	window.addstr(9, 0, "either 3. or 3:). The four free cells in the")
	window.addstr(10, 0, "upper left corner will accept any cards, but")
	window.addstr(11, 0, "at most one card per cell.")
	window.addstr(13, 0, "Type any character to continue.    Page 1(4)")
	window.attrset(curses.color_pair(1))
	window.addstr(6, 35, "2")
	window.addstr(6, 36, suitesymbols[3])
	window.addstr(7, 3, "1")
	window.addstr(7, 4, suitesymbols[3])
	window.addstr(8, 39, "2")
	window.addstr(8, 40, suitesymbols[3])
	window.attrset(curses.A_BOLD)
	window.addstr(9, 7, "3")
	window.addstr(9, 8, suitesymbols[0])
	window.addstr(9, 13, "3")
	window.addstr(9, 14, suitesymbols[2])
	window.attrset(curses.A_NORMAL)
	window.move(12, 43)
	window.refresh()
	window.getch()
	window.erase()
	window.addstr(0, 0, "freecell " + RELEASE)
	window.addstr(0, 24, "www.linusakesson.net")
	window.addstr(2, 0, "To move a card,  type the name of the column")
	window.addstr(3, 0, "(a-h) or cell (w-z) which contains the card,")
	window.addstr(4, 0, "followed by the name of the destination cell")
	window.addstr(5, 0, "or column. Press the enter key for the dest-")
	window.addstr(6, 0, "ination in order to  move the card to one of")
	window.addstr(7, 0, "the foundation piles.  As a convenience, you")
	window.addstr(8, 0, "may also move a card to an unspecified  free")
	window.addstr(9, 0, "cell,  by substituting the space bar for the")
	window.addstr(10, 0, "destination.")
	window.addstr(13, 0, "Type any character to continue.    Page 2(4)")
	window.attrset(curses.color_pair(4))
	window.addstr(3, 1, "a")
	window.addstr(3, 3, "h")
	window.addstr(3, 15, "w")
	window.addstr(3, 17, "z")
	window.addstr(5, 21, "enter")
	window.addstr(9, 27, "space")
	window.attrset(curses.A_NORMAL)
	window.move(12, 43)
	window.refresh()
	window.getch()
	window.erase()
	window.addstr(0, 0, "freecell " + RELEASE)
	window.addstr(0, 24, "www.linusakesson.net")
	window.addstr(2, 0, "While you may only move one card at a time,")
	window.addstr(3, 0, "you can use free cells and empty columns as")
	window.addstr(4, 0, "temporary buffers. That way, it is possible")
	window.addstr(5, 0, "to move a range of cards from one column to")
	window.addstr(6, 0, "another,  as long as they are already in an")
	window.addstr(7, 0, "acceptable order.   The program can do this")
	window.addstr(8, 0, "automatically for you:  Prefix your command")
	window.addstr(9, 0, "with the number of cards to move,  e.g. 3ab")
	window.addstr(10, 0, "will move 3 cards from column a to column b")
	window.addstr(11, 0, "and requires 2 free cells or empty columns.")
	window.addstr(13, 0, "Type any character to continue.    Page 3(4)")
	window.attrset(curses.color_pair(4))
	window.addstr(9, 40, "3ab")
	window.attrset(curses.A_NORMAL)
	window.move(12, 43)
	window.refresh()
	window.getch()
	window.erase()
	window.addstr(0, 0, "freecell " + RELEASE)
	window.addstr(0, 24, "www.linusakesson.net")
	window.addstr(2, 0, "When it is deemed safe to do so,  cards will")
	window.addstr(3, 0, "automatically  be  moved  to  the foundation")
	window.addstr(4, 0, "piles.")
	window.addstr(6, 0, "Modern freecell was invented by Paul Alfille")
	window.addstr(7, 0, "in 1978 - http://wikipedia.org/wiki/Freecell")
	window.addstr(8, 0, "Almost every game is solvable, but the level")
	window.addstr(9, 0, "of difficulty can vary a lot.")
	window.attrset(curses.color_pair(4))
	window.addstr(11, 0, "   Good luck, and don't get too addicted!")
	window.attrset(curses.A_NORMAL)
	window.addstr(13, 0, "Type any character to continue.    Page 4(4)")
	window.move(12, 43)
	window.refresh()
	window.getch()

def render():
	wheight, wwidth = window.getmaxyx()
	col_height = max([len(i) for i in columns])
	if (wheight < col_height + 7) or wwidth < 46:
		curses.resizeterm(col_height + 7, 46) # increse height to fit the initial display
		window.refresh()
	window.erase()
	window.addstr(0, 0, "space                                  enter")
	seedstr = f'#{seed}'
	window.addstr(0, 22 - len(seedstr) // 2, seedstr) # centred game number
	window.addstr(1, 0, '[   ][   ][   ][   ]    [   ][   ][   ][   ]')
	# arguments of face between work and pile stacks
	window.move(1, 21)
	window.attrset(curses.A_BOLD | curses.color_pair(4))
	if arg:
		window.addstr(str(arg))
	else:
		window.addstr(['=)' if face else '(='][0])
	window.attrset(curses.A_NORMAL)
	for i, card in enumerate(work):
		window.move(1, 1 + 5 * i)
		sel = False
		if wselected and selcol == i:
			sel = True
		if card:
			card.show(sel)
			window.addch(2, 2 + 5 * i, chr(ord('w')+i))
	for i, card in enumerate(pile):
		window.move(1, 25 + 5 * i)
		if card:
			card.show(False)
	for colidx, column in enumerate(columns):
		for cardidx, card in enumerate(column):
			window.move(4 + cardidx, 3 + 5 * colidx)
			sel = False
			if selected and (selcol == colidx) and (cardidx >= len(column) - seln):
				sel = True
			card.show(sel)
	window.addstr(5 + col_height, 0, "    a    b    c    d    e    f    g    h")
	statstr = f'{nmoves} move{"" if nmoves==1 else "s"}, {nundos} undo{"" if nundos==1 else "s"}'
	window.addstr(6 + col_height, 44 - len(statstr), statstr)
	window.addstr(6 + col_height, 0, 'quit undo ?=help')
	window.attrset(curses.color_pair(1))
	window.addch(6 + col_height, 0, 'q')
	window.addch(6 + col_height, 5, 'u')
	window.addch(6 + col_height, 10, '?')
	window.attrset(curses.A_NORMAL)
	window.move(5 + col_height, 43)
	window.refresh()


window = curses.initscr()
curses.noecho()
curses.curs_set(0)
window.keypad(True)
curses.start_color()
curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLUE)
curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)
columns = dealgame(seed)
running = True
while running:
	while True:
		render()
		if automove():
			time.sleep(0.05)
		else:
			break
	if gameover():
		gameover_animation()
		break

	c = window.getch()
	if ord('0') <= c <= ord('9'):
		if (arg < 10) and (not selected) and (not wselected):
			arg = arg * 10 + int(chr(c)) # allows inputting 2-digit numbers
	else:
		if c == ord(' '): # pressed space
			if selected or wselected: # try to move card to next free work slot
				for i in range(4): # find first empty slot
					if not work[i]:
						break
				if i < 4: # found slot
					c = ord('w')+i # replace space by slot char
				else:
					c = 27 # ESC
					face = 0 # flip face
		if c == ord('q'):
			running = 0
		elif c == 27: # ESC
			selected = False
			wselected = False
		elif c == ord('u'):
			popundo()
		elif c == ord('?'):
			helpscreen()
		elif c == curses.KEY_ENTER or c == 10 or c == 13: # try to move to foundation pile
			may = False
			if selected:
				col = columns[selcol]
				if seln == 1 and len(col): # there is a selected card
					card = col[-1] # get the card
					if pile[card.kind]: # can move if higher card on foundation
						if card.value == pile[card.kind].value + 1:
							may = True
					else: # or if it is the first card
						if card.value == 1:
							may = True
					if may:
						pushundo() # save game state before move
						pile[card.kind] = card # move the card
						col.pop()
				selected = False
			elif wselected: # card on the work pile selected
				if work[selcol]:
					card = work[selcol] # get the card
					if pile[card.kind]: # can move if higher card on foundation
						if card.value == pile[card.kind].value + 1:
							may = True
					else: # or if it is the first card
						if card.value == 1:
							may = True
					if may:
						pushundo() # save game state before move
						pile[card.kind] = card # move the card
						work[selcol] = None
				wselected = False
			face = 1
		elif ord('a') <= c <= ord('h'):
			col = columns[c - ord('a')]
			may = False
			if selected: # if cards in the columns are selected
				nfree = work.count(None) + columns.count([]) # how many free slots are available?
				if nfree >= seln - 1 + (not len(col)): # if one of the free slots is the target, can't use it to move
					first_card = columns[selcol][-seln] #
					may = True
					if col and ((first_card.kind & 1) == (col[-1].kind & 1)): # if both are even orr odd suits
						may = False
					if col and (first_card.value + 1 != col[-1].value): # if not next smaller value
						may = False
					if may:
						pushundo() # save game state
						col.extend(columns[selcol][-seln:])
						columns[selcol] = columns[selcol][:-seln]
				selected = False
			elif wselected: # if columns in the work pile are selected
				if col: # to put in column, opposite suites and next smaller value is needed
					if ((col[-1].kind & 1) != (work[selcol].kind & 1)) and (col[-1].value == work[selcol].value + 1):
						may = True
				else: # if the column is empty, card can always be placed
					may = True
				if may:
					pushundo() # save game state
					col.append(work[selcol])
					work[selcol] = None
				wselected = False
			else: # nothing selected, so select now
				selcol = c - ord('a') # the selected column
				if columns[selcol]:
					selected = True
					seln = arg if arg else 1
					maxn = 1
					for i in range(len(columns[selcol])-1,0,-1): # go backwards through the column
						card = columns[selcol][i]
						card_above = columns[selcol][i-1]
						if ((card.kind & 1) != (card_above.kind & 1)) and (card.value + 1 == card_above.value):
							maxn += 1
						else: # stop if chain broken
							break
					if seln > maxn:
						seln = maxn # limit selection to chain length
			face = c >= ord('e') # look on the bright (selected) side
		elif ord('w') <= c <= ord('z'): # a location in the work pile was entered
			w = c - ord('w') # index in work pile
			if selected:
				col = columns[selcol]
				if (seln == 1) and (not work[w]) and len(col): # can move from column to work
					pushundo() # save game state
					work[w] = col.pop() # move the card
				selected = False
			elif wselected:
				if not work[w]: # move from work to other empty work slot
					pushundo()
					work[w] = work[selcol]
					work[selcol] = None
				wselected = False
			else:
				if work[w]: # if nothing was selected, just select now
					wselected = True
					selcol = w
			face = 0
		arg = 0

curses.curs_set(1)
curses.echo()
curses.endwin()
