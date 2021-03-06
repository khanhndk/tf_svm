import tensorflow as tf
import numpy as np


class RepTrickSVM:
    """
    Support Vector Machine with Random Feature Space using Tensorflow
    with Reparameterization Trick
    """
    def __init__(
            self,
            trade_off=1.0,
            gamma_init_value=1.0,
            batch_size=10,
            rf_dim=400,
            learning_rate=1e-3,
            num_epochs=2,
    ):
        self.trade_off = trade_off
        self.gamma_init_value = gamma_init_value
        self.batch_size = batch_size
        self.rf_dim = rf_dim
        self.learning_rate = learning_rate
        self.num_epochs = num_epochs

    def _init_params_pre_build_graph(self):
        """
        Initialize some params before building computational graph
        """
        pass  # there is nothing to initialize

    def _init_params_post_build_graph(self):
        """
        Initialize some params after building computational graph
        """
        self.epsilon_value = np.random.multivariate_normal(
            mean=np.zeros(self.input_dim),
            cov=np.eye(self.input_dim),
            size=self.rf_dim
        )

    def _build_graph(self, x, y):
        """
        Build computational graph
        :param x: (num_samples, input_dim)
        :param y: (num_samples,)
        """
        self._init_params_pre_build_graph()

        self.input_dim = x.shape[1]
        self.x = tf.placeholder(dtype=tf.float32, shape=[self.batch_size, self.input_dim])
        self.y = tf.placeholder(dtype=tf.float32, shape=[self.batch_size])

        self.epsilon = tf.placeholder(dtype=tf.float32, shape=[self.rf_dim, self.input_dim])
        self.gamma_init = self.gamma_init_value * np.ones(self.input_dim)
        self.gamma = tf.Variable(initial_value=self.gamma_init, dtype=tf.float32)
        self.omega = self.epsilon * self.gamma

        self.omega_x = tf.matmul(self.x, tf.transpose(self.omega))  # (self.batch_size, self.rf_dim)
        self.cos_omega_x = tf.cos(self.omega_x)
        self.sin_omega_x = tf.sin(self.omega_x)
        self.phi_x = tf.concat([self.cos_omega_x, self.sin_omega_x], axis=1)
        # phi_x.shape = (batch_size, 2*rf_dim)

        self.w_init = np.zeros(self.rf_dim * 2)
        self.w = tf.Variable(initial_value=self.w_init, dtype=tf.float32)
        self.b_init = 1.0
        self.b = tf.Variable(initial_value=self.b_init, dtype=tf.float32)

        self.predict_value = tf.reduce_sum(self.phi_x * self.w, axis=1) + self.b
        self.loss = tf.losses.hinge_loss(self.y, self.predict_value)
        self.mean_loss = tf.reduce_mean(self.loss)
        self.regularization_term = 0.5 * tf.reduce_sum(tf.square(self.w))
        self.objective_function = self.regularization_term + self.trade_off * self.mean_loss
        self.optimizer = tf.train.GradientDescentOptimizer(learning_rate=self.learning_rate)
        self.trainer = self.optimizer.minimize(self.objective_function)

        self.session = tf.Session()
        self.session.run(tf.global_variables_initializer())

        self._init_params_post_build_graph()

    def fit(self, x, y):
        """
        Learn model
        :param x: (num_samples, input_dim)
        :param y: (num_samples,)
        """
        num_samples = x.shape[0]
        self._build_graph(x, y)

        num_iterations = int(self.num_epochs * num_samples / self.batch_size)

        for it in range(num_iterations):
            idx_samples = np.random.randint(0, num_samples, self.batch_size)
            feed_data = {
                self.x: x[idx_samples, :],
                self.y: y[idx_samples],
                self.epsilon: self.epsilon_value,
            }
            _, loss = self.session.run([self.trainer, self.mean_loss], feed_dict=feed_data)
            print('Iter', it, ': loss=', loss)

    def predict(self, x_test):
        """
        Predict labels
        :param x_test: (num_tests, input_dim)
        """
        num_tests = x_test.shape[0]
        y_predict = np.ones(num_tests, dtype=int)

        num_padding_test = int(np.ceil(num_tests / self.batch_size) * self.batch_size)
        idx_test = np.zeros(num_padding_test, dtype=int)
        idx_test[0:num_tests] = np.arange(0, num_tests)

        for it in range(0, num_padding_test, self.batch_size):
            idx_batch = idx_test[it:it+self.batch_size]
            feed_data = {
                self.x: x_test[idx_batch, :],
                self.y: y_predict[idx_batch],
                self.epsilon: self.epsilon_value,
            }

            predict_value = self.session.run(self.predict_value, feed_dict=feed_data)
            y_predict[idx_batch] = np.sign(predict_value)

        return y_predict
