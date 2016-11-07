import logging.config


logging.config.fileConfig('logging.conf')
logger = logging.getLogger('tmp')

def gen():
  logger.debug('gen: function started!')
  a = yield
  logger.debug('gen: before while!')
  while a != 0:
    logger.debug('gen: while first')
    a = yield 'value is %d!' % a
    logger.debug('gen: while last')
  yield a

def test():
  z = gen()
  next(z)
  print(z.send(1))
  print(z.send(2))
  print(z.send(3))
  print(z.send(4))
  print(z.send(0))


def gen2_helper0():
  yield 'gen2_helper0 - that''s all'
  print('    >> exit function for branch 0!')
  

def gen2_helper1():
  a = yield 'gen2_helper1 - expecting something more'
  yield 'that is: %d' % a
  print('    >> exit function for branch 1!')

def gen2():
  a = None
  print('    >> before while!')
  while a != -1:
    print('    >> while start!')
    a = yield
    if a == 0:
      print('    >> start branch 0!')
      yield from gen2_helper0()
    elif a == 1:
      print('    >> start branch 1!')
      yield from gen2_helper1()
    else:
      yield 'zuzuzu'
    print('    >> while finished!')

  
