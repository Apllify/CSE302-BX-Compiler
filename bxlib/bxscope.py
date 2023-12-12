# --------------------------------------------------------------------
import contextlib as cl
import typing as tp

# ====================================================================
class Scope:
    def __init__(self):
        self.vars = [dict()]

    def open(self):
        self.vars.append(dict())

    def close(self):
        assert(len(self.vars) > 0)
        self.vars.pop()

    def push(self, name: str, data: tp.Any):
        assert(name not in self.vars[-1])
        self.vars[-1][name] = data

    def islocal(self, name: str):
        return name in self.vars[-1]

    def __getitem__(self, name: str):
        for s in self.vars[::-1]:
            if name in s:
                return s[name]
        assert(False)

    def __setitem__(self, name: str, newdata : tp.Any):
        if name not in self : 
            return self.push(name, newdata)

        #set value in most recent scope 
        for i in range(len(self.vars) - 1, -1, -1):
            if name in self.vars[i]:
                self.vars[i][name] = newdata
                break


    def __contains__(self, name: str):
        return any(name in s for s in self.vars)

    @cl.contextmanager
    def in_subscope(self):
        self.open()
        try:
            yield self
        finally:
            self.close()
