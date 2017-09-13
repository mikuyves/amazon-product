import leancloud


class Prod(leancloud.Object):
    # ASIN
    @property
    def asin(self):
        return self.get('asin')

    @asin.setter
    def asin(self, value):
        return self.set('asin', value)

    # name
    @property
    def name(self):
        return self.get('name')

    @name.setter
    def name(self, value):
        return self.set('name', value)

    # max_price
    @property
    def max_price(self):
        return self.get('max_price')

    @max_price.setter
    def max_price(self, value):
        return self.set('max_price', value)

    # min_price
    @property
    def min_price(self):
        return self.get('min_price')

    @min_price.setter
    def min_price(self, value):
        return self.set('min_price', value)


class Sku(leancloud.Object):
    # ASIN
    @property
    def asin(self):
        return self.get('asin')

    @asin.setter
    def asin(self, value):
        return self.set('asin', value)

    # name
    @property
    def name(self):
        return self.get('name')

    @name.setter
    def name(self, value):
        return self.set('name', value)

    # Current price.
    @property
    def price(self):
        return self.get('price')

    @price.setter
    def price(self, value):
        return self.set('price', value)

    # Top price in history.
    @property
    def top_price(self):
        return self.get('top_price')

    @top_price.setter
    def top_price(self, value):
        return self.set('top_price', value)

    # Bottom price in history.
    @property
    def bottom_price(self):
        return self.get('bottom_price')

    @bottom_price.setter
    def bottom_price(self, value):
        return self.set('bottom_price', value)
