import gym
import tensorflow as tf
import numpy as np

env = gym.make("CartPole-v1")
obs = env.reset()

n_inputs = 4

model = tf.keras.models.Sequential([
    tf.keras.layers.Dense(5, activation='elu', input_shape=[n_inputs]),
    tf.keras.layers.Dense(1, activation='sigmoid')
])

n_iterations = 150
n_eps_per_update = 10
n_max_steps = 200
discount_factor = 0.95

optimizer = tf.keras.optimizers.Adam(lr=0.01)
loss_fn = tf.keras.losses.binary_crossentropy


def play_one_step(env, obs, model, loss_fn):
    with tf.GradientTape() as tape:
        left_proba = model(obs[np.newaxis])
        action = (tf.random.uniform([1,1]) > left_proba)
        y_target = tf.constant([[1.]]) - tf.cast(action, tf.float32)
        loss = tf.reduce_mean(loss_fn(y_target, left_proba))
    grads = tape.gradient(loss, model.trainable_variables)
    obs, reward, done, info = env.step(int(action[0,0].numpy()))
    return obs, reward, done, grads


def play_multiple_episodes(env, n_episodes, n_max_steps, model, loss_fn):
    all_rewards = []
    all_grads = []
    for episode in range(n_episodes):
        env.render()
        curr_rew = []
        curr_grads = []
        obs = env.reset()
        for step in range(n_max_steps):
            obs, reward, done, grads = play_one_step(env, obs, model, loss_fn)
            curr_rew.append(reward)
            curr_grads.append(grads)
            if done:
                break
        all_rewards.append(curr_rew)
        all_grads.append(curr_grads)
    return all_rewards, all_grads


def discount_rewards(rewards, discount_factor):
    discounted = np.array(rewards)
    for step in range(len(rewards) -2, -1, -1):
        discounted[step] += discounted[step + 1] * discount_factor
    return discounted


def discount_and_normalize_rewards(all_rewards, discount_factor):
    all_discounted_rewards = [discount_rewards(rewards, discount_factor) for rewards in all_rewards]
    flat_rewards = np.concatenate(all_discounted_rewards)
    reward_mean = flat_rewards.mean()
    reward_std = flat_rewards.std()
    return[(discounted_rewards - reward_mean) / reward_std for discounted_rewards in all_discounted_rewards]


for iteration in range(n_iterations):
    all_rewards, all_grads = play_multiple_episodes(env, n_eps_per_update, n_max_steps, model, loss_fn)
    all_final_rewards = discount_and_normalize_rewards(all_rewards, discount_factor)

    all_mean_grads = []
    for var_index in range(len(model.trainable_variables)):
        mean_grads = tf.reduce_mean([final_reward * all_grads[episode_index][step][var_index]
                                     for episode_index, final_rewards in enumerate(all_final_rewards)
                                     for step, final_reward in enumerate(final_rewards)], axis=0)
        all_mean_grads.append(mean_grads)
    optimizer.apply_gradients(zip(all_mean_grads, model.trainable_variables))