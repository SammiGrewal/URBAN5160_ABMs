import mesa
import seaborn as sns
import numpy as np
import pandas as pd


class MoneyAgent(mesa.Agent):
    """An agent with fixed initial wealth."""

    def __init__(self, model):
        #pass the parameter to the parent class.
        super().__init__(model)

        #create the agent's variable and set the initial values.
        self.wealth = 1

    def exchange(self):
        #verify agent has some wealth
        if self.wealth > 0:
            other_agent = self.random.choice(self.model.agents)
            if other_agent is not None:
                other_agent.wealth += 1
                self.wealth -= 1

    def say_hi(self):
        #the agent's step will go here.
        #for demonstration purposes we will print the agent\s unique_id
        #print(f"Hi, I am an agent, you can call me {str(self.unique_id)}.")
        print(f"I am {str(self.unique_id)} and I now have {str(self.wealth)} money")

class MoneyModel(mesa.Model):
    """A model with some number of agents."""

    def __init__(self, n, seed=None):
        super().__init__(seed=seed)
        self.num_agents = n
        #create agents
        MoneyAgent.create_agents(model=self, n=n)

    def step(self):
        """Advance the model by one step."""

        #this function pseudo-randomly reorders the list of agent objects and
        #then iterates through calling the function passed in as the parameter
        self.agents.do("say_hi")
        self.agents.shuffle_do("exchange")



