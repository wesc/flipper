
import flipper_model

from collections import namedtuple


if __name__ == '__main__':
    m = flipper_model.FlipperModel('test.db')
    m.init_tables()
    m.create_user('wesc', 'wescpass')
    m.create_user('roy', 'roypass')
    m.create_user('joe', 'joejoe')

    print m._fetchall('SELECT * FROM users')
