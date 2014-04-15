# -*- coding: utf-8 -*-


class HookStatus(Exception):
    def __init__(self, status, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)

        self.status = status
