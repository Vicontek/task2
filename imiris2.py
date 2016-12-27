# coding: utf-8

# In[1018]:

import simpy as smp
from random import expovariate, random, randint


# In[1019]:

def print_time(s, sec):
    mins = str(int(sec // 60))
    secs = int(sec %  60)
    if secs // 10 == 0:
        secs = "0" + str(secs)
    else:
        secs = str(secs)
    print(s, mins + ":" + secs)


# In[1020]:

def discrete_rv(drv):
    if sum([val[0] for val in drv]) != 1:
        raise 1
    r = random()
    s = 0
    for pair in drv:
        if (r > s) and (r < (s + pair[0])):
            return pair[1]
        s += pair[0]


# In[1021]:

CUSTOMER_DSTRB = [[0.5, 1], [0.3, 2], [0.1, 3], [0.1, 4]]
WAY_DSTRB = [[0.8, "hot"], [0.15, "cold"], [0.05, "drinks"]]
CASHBOX_NUMBER = 2
MEAN_GAP = 30
CUSTOMER_NUMBER = 0
STUDETNTS = []


# In[1022]:

def gen_group(env, canteen):
    global CUSTOMER_NUMBER, STUDETNTS
    env.process(canteen.start())
    while True:
        yield env.timeout(expovariate(1 / MEAN_GAP))
        n = discrete_rv(CUSTOMER_DSTRB)
        for i in range(n):
            std = Student(env, canteen, CUSTOMER_NUMBER)
            STUDETNTS += [std]
            env.process(std.start())
            CUSTOMER_NUMBER += 1


# In[1023]:

class Student:
    def __init__(self, env, canteen, index):
        self.env = env
        self.canteen = canteen
        self.index = index
        self.service_time = 0
        self.cashbox_time = 0
        self.delays = {"hot":0, "cold":0, "cash":0}
        self.cash_wait = 0
        self.finished = 0
        
    def start(self):
        self.service_time = self.env.now
        self.way = discrete_rv(WAY_DSTRB)
        print("Студент {0} направился к {1}".format(self.index, self.way))
        if self.way != "drinks":
            with self.canteen.stations[self.way][0].request() as req:
                self.canteen.stations[self.way][2] += 1
                wait = self.env.now
                yield req
                
                self.canteen.stations[self.way][2] -= 1
                self.delays[self.way] = self.env.now - wait
                print("Студент {0} начал обслуживание у {1}_station в {2}".format(self.index, self.way, self.env.now))
                
                yield self.env.process(self.canteen.stations[self.way][1](self))
                print("Студент {0} покинул {1}_station в {2}".format(self.index, self.way, self.env.now))
        
        print("Студент {0} начал обслуживание у drinks_station  в {1}".format(self.index, self.env.now))
        yield self.env.process(self.canteen.drinks_station(self))
        print("Студент {0} покинул drinks_station в {1}".format(self.index, self.env.now))
               
        cash_n, cashbox, q_len = min(self.canteen.cashboxes, key=lambda x: x[2])
        print([cbox[2] for cbox in self.canteen.cashboxes])
        print("Студент {0} прибыл к кассе #{1} в {2}".format(self.index, cash_n,  self.env.now))
        
        
        self.canteen.cashboxes[cash_n][2] += 1
        wait = self.env.now
        
        with cashbox.request() as cash_req:
            yield cash_req
            self.delays["cash"] = self.env.now - wait
            print("Студент {0} начал обслуживание у кассы #{1} в {2}".format(self.index, cash_n, self.env.now))
            
            yield self.env.process(self.canteen.cashbox(self))
            print("Студент {0} покинул кассу #{1} в {2}".format(self.index, cash_n, self.env.now))
            self.canteen.cashboxes[cash_n][2] -= 1
            
        self.finished = 1
        self.service_time = self.env.now - self.service_time
        print_time("Студент {0} обслуживался".format(self.index), self.service_time)


# In[1024]:

class Canteen:
    def __init__(self, env):
        self.env = env
        self.hot = smp.Resource(self.env, capacity=1)
        self.cold = smp.Resource(self.env, capacity=1)
        self.cashboxes = [[i, smp.Resource(self.env, capacity=1), 0] for i in range(CASHBOX_NUMBER)]
        self.stations = {"hot":[self.hot, self.hot_station, 0], "cold":[self.cold, self.cold_station, 0]}
    
    def hot_station(self, student):
        time = randint(50, 120)
        student.cashbox_time += randint(20, 40)
        print("hot time:", time)
        yield student.env.timeout(time)
    
    def cold_station(self, student):
        time = randint(60, 180)
        student.cashbox_time += randint(5, 15)
        print("{0} student's cold time:".format(student.index), time)
        yield student.env.timeout(time)
    
    def drinks_station(self, student):
        time = randint(5, 20)
        student.cashbox_time += randint(5, 10)
        print("drinks time:", time)
        yield student.env.timeout(time) 
    
    def cashbox(self, student):
        yield student.env.timeout(student.cashbox_time)
        
    def start(self):
        self.mean_hot_queue  = 0
        self.mean_cold_queue = 0
        self.mean_cash_queue = 0
        self.mean_all = 0
        
        self.max_hot_queue  = 0
        self.max_cold_queue = 0
        self.max_cash_queue = 0
        self.max_all = 0
        tick = 0
        while True:
            yield self.env.timeout(1)
            self.mean_hot_queue = self.mean_hot_queue * tick + self.stations["hot"][2]
            self.mean_cold_queue = self.mean_cold_queue * tick + self.stations["cold"][2]
            self.mean_cash_queue = self.mean_cash_queue * tick + sum([cash[2] for cash in self.cashboxes]) / CASHBOX_NUMBER
            all_students = self.stations["hot"][2] + self.stations["cold"][2] + sum([cash[2] for cash in self.cashboxes])
            self.mean_all = self.mean_all * tick + all_students
            tick += 1 
            
            self.mean_hot_queue /= tick
            self.mean_cold_queue /= tick
            self.mean_cash_queue /= tick
            self.mean_all /= tick
            
            if self.stations["hot"][2] > self.max_hot_queue:
                self.max_hot_queue = self.stations["hot"][2]
            if self.stations["cold"][2] > self.max_cold_queue:
                self.max_cold_queue = self.stations["cold"][2]
            if max([cash[2] for cash in self.cashboxes]) > self.max_cash_queue:
                self.max_cash_queue = max([cash[2] for cash in self.cashboxes])
            if all_students > self.max_all:
                self.max_all = all_students
        
        


# In[ ]:




# In[1025]:

env = smp.Environment()
cnt = Canteen(env)
env.process(gen_group(env, cnt))
env.run(until=90*60)


# In[1026]:

mn_hot = sum([std.delays["hot"] for std in STUDETNTS if (std.way == "hot" and std.finished)]) / len([std for std in STUDETNTS if (std.way == "hot" and std.finished)])
print_time("Mean hot delay:", mn_hot)
mx_hot = max([std.delays["hot"] for std in STUDETNTS if std.way == "hot"])
print_time("Max  hot delay", mx_hot)


# In[1027]:

mn_cold = sum([std.delays["cold"] for std in STUDETNTS if (std.way == "cold" and std.finished)]) / len([std for std in STUDETNTS if (std.way == "cold" and std.finished)])
print_time("Mean cold delay:", mn_cold)
mx_cold = max([std.delays["cold"] for std in STUDETNTS if std.way == "cold"])
print_time("Max  cold delay:", mx_cold)


# In[1028]:

mn_cash = sum([std.delays["cash"] for std in STUDETNTS if std.finished]) / len([std for std in STUDETNTS if std.finished])
mx_cash = max([std.delays["cash"] for std in STUDETNTS if std.finished])
print_time("Mean cash delay:", mn_cash)
print_time("Max  cash delay:", mx_cash)
max([std.delays["cash"] for std in STUDETNTS if std.finished])


# In[1029]:

print("Mean hot_station queue:", int(cnt.mean_hot_queue))
print("Max  hot_station queue:", cnt.max_hot_queue)


# In[1030]:

print("Mean cold_station queue:", int(cnt.mean_cold_queue))
print("Max  cold_station queue:", cnt.max_cold_queue)


# In[1031]:

print("Mean cashbox queue:", int(cnt.mean_cash_queue))
print("Max  cashbox queue:", cnt.max_cash_queue)


# In[1032]:

type1 = [std for std in STUDETNTS if (std.way == "hot" and std.finished)]
type2 = [std for std in STUDETNTS if (std.way == "cold" and std.finished)]
type3 = [std for std in STUDETNTS if (std.way == "drinks" and std.finished)]
types = [type1, type2, type3]

for i in range(len(types)):
    print_time("Mean queue delay for type{0}:".format(i+1), sum([sum(std.delays.values()) for std in types[i]]) / len(types[i]))
    print_time("Max  queue delay for type{0}:".format(i+1), max([sum(std.delays.values()) for std in types[i]]))
    print()


# In[ ]:




# In[ ]:




# In[1033]:

mn_total = sum([sum(std.delays.values()) for std in STUDETNTS if std.finished]) / len([std for std in STUDETNTS if std.finished])
print_time("Mean total service time:", mn_total)

