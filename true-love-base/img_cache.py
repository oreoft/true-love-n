from collections import OrderedDict


class ImgMsgCache:
    def __init__(self, capacity=500):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        """
        根据key获取value。如果key存在，将其移到最后（表示最近使用）。
        """
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key, value):
        """
        添加或更新键值对，并将其移到最后（表示最近使用）。
        如果缓存超过最大容量，则移除最早的元素。
        """
        if key in self.cache:
            # 更新已有的键值对
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)  # 移除最早的元素
