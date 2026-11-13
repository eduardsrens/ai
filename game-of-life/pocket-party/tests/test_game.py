import random
import unittest
from unittest.mock import Mock
import game

class PartyTests(unittest.TestCase):
 def party(self):return game.ready(game.start(game.new_game(),['Sunny','River','Clover','Plum']))
 def test_setup_and_handoff(self):
  g=game.new_game()
  with self.assertRaises(ValueError):game.start(g,['A','a'])
  game.start(g,['A','B']);self.assertEqual(g['phase'],'handoff')
  with self.assertRaises(ValueError):game.spin(g)
  game.ready(g);self.assertEqual(g['phase'],'playing')
 def test_one_roll_per_turn(self):
  g=self.party();game.spin(g,random.Random(1))
  if g['pending']:game.choose(g,'skip')
  with self.assertRaises(ValueError):game.spin(g)
  game.end_turn(g);self.assertEqual(g['current'],1);self.assertEqual(g['phase'],'handoff')
 def test_item_damage_shield_and_once_per_turn(self):
  g=self.party();g['players'][1]['shield']=True
  game.use_item(g,'rocket',1)
  self.assertEqual(g['players'][1]['hp'],20);self.assertFalse(g['players'][1]['shield'])
  with self.assertRaises(ValueError):game.use_item(g,'shield')
 def test_knockout_and_magnet(self):
  g=self.party();p=g['players'][1];p.update(hp=3,position=18,keys=12)
  game.use_item(g,'rocket',1);self.assertEqual((p['hp'],p['position'],p['keys']),(20,0,4))
  g['used_item']=False;g['players'][0]['items'].append('magnet');game.use_item(g,'magnet',1)
  self.assertEqual(p['keys'],0);self.assertEqual(g['players'][0]['keys'],14)
 def test_chest_pass_and_purchase(self):
  g=self.party();g['players'][0].update(position=6,keys=20)
  rng=Mock();rng.randint.return_value=2
  game.spin(g,rng);self.assertIsNotNone(g['pending'])
  game.choose(g,'buy');self.assertEqual(g['players'][0]['trophies'],1)
  self.assertEqual(g['players'][0]['keys'],8)
 def test_cannot_buy_without_keys(self):
  g=self.party();g['players'][0].update(position=6,keys=0)
  rng=Mock();rng.randint.return_value=1;game.spin(g,rng)
  with self.assertRaises(ValueError):game.choose(g,'buy')
 def test_roll_wraps_portal(self):
  g=self.party();g['players'][0]['position']=47;rng=Mock();rng.randint.return_value=3
  game.spin(g,rng);self.assertEqual(g['players'][0]['position'],1)
 def test_five_complete_parties(self):
  for seed in range(5):
   rng=random.Random(seed);g=self.party()
   while g['phase']!='finished':
    if g['phase'] in ('handoff','minigame_handoff'):game.ready(g)
    elif g['phase']=='playing':
     game.spin(g,rng)
     if g['pending']:game.choose(g,'buy' if g['players'][g['current']]['keys']>=20 else 'skip')
     game.end_turn(g)
    elif g['phase']=='minigame':
     g['mini']['started']-=6
     game.minigame(g,dict(elapsed=460,answer=g['mini'].get('gems',[]).count('gold') if g['mini'].get('gems') else 0,taps=rng.randint(10,40)))
    elif g['phase']=='round_results':game.next_round(g)
   self.assertEqual(g['round'],8)
   self.assertTrue(all(p['hp']>0 and p['keys']>=0 for p in g['players']))
   self.assertGreaterEqual(sum(p['trophies'] for p in g['players']),8)

if __name__=='__main__':unittest.main()
