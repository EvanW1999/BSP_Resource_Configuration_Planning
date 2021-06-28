from gym import Env
import keras
from keras.models import Sequential
from keras.layers import Flatten, Dense
from keras.optimizers import Adam
from rl.agents import DQNAgent, SARSAAgent
from rl.policy import EpsGreedyQPolicy, GreedyQPolicy, BoltzmannQPolicy
from rl.memory import SequentialMemory


def agent(states, actions):
    model = Sequential()
    model.add(Flatten(input_shape=(1, ) + states))
    model.add(Dense(24, activation='relu'))
    model.add(Dense(24, activation='relu'))
    model.add(Dense(24, activation='relu'))
    model.add(Dense(actions, activation='linear'))
    return model


def build_agent(model, actions):
    # policy = EpsGreedyQPolicy()
    policy = BoltzmannQPolicy()
    memory = SequentialMemory(limit=50000, window_length=1)
    # dqn = SARSAAgent(model=model, nb_actions=actions,
    #                  policy=policy, nb_steps_warmup=100)
    dqn = DQNAgent(model=model, memory=memory, policy=policy,
                   nb_actions=actions, nb_steps_warmup=100, target_model_update=1e-2)
    return dqn


def train_keras_dqn(env: Env) -> None:
    states = env.observation_space.shape
    print(states)
    actions = env.action_space.n
    keras.backend.clear_session()
    model: Sequential = agent(states, actions)
    for _ in range(30):
        print(env.action_space.sample())
    dqn = build_agent(model, actions)
    dqn.compile(Adam(lr=1e-3), metrics=['mae'])
    dqn.fit(env, nb_steps=100000, visualize=False, verbose=1)
    dqn.save_weights("boltzman_dqn_w2_a3.h5f", overwrite=True)
    dqn.load_weights("weights.h5f")
