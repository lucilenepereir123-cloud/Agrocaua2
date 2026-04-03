"""
Modelos de ML simplificados (sem dependencias externas)
Implementacoes de LogisticRegression e LinearRegression do zero com numpy.
"""

import numpy as np
import pickle


class SimpleLogisticRegression:
    """Regressao Logistica com gradient descent e sigmoid numericamente estavel."""

    def __init__(self, learning_rate=0.01, n_iterations=1000):
        self.learning_rate = learning_rate
        self.n_iterations  = n_iterations
        self.weights       = None
        self.bias          = None
        self.is_fitted     = False

    def sigmoid(self, z):
        """
        Sigmoid numericamente estavel.
        Clip de z para [-500, 500] elimina overflow sem alterar o resultado:
        sigmoid(-500) e sigmoid(500) sao indistinguiveis de 0.0 e 1.0 em float64.
        """
        return 1.0 / (1.0 + np.exp(-np.clip(z, -500.0, 500.0)))

    def fit(self, X, y):
        """Treinar o modelo com gradient descent."""
        n_samples, n_features = X.shape
        self.weights = np.zeros(n_features)
        self.bias    = 0.0

        for _ in range(self.n_iterations):
            linear_model = np.dot(X, self.weights) + self.bias
            y_predicted  = self.sigmoid(linear_model)

            dw = (1.0 / n_samples) * np.dot(X.T, (y_predicted - y))
            db = (1.0 / n_samples) * np.sum(y_predicted - y)

            self.weights -= self.learning_rate * dw
            self.bias    -= self.learning_rate * db

        self.is_fitted = True
        return self

    def predict_proba(self, X):
        """Retornar probabilidades [P(0), P(1)] para cada amostra."""
        if not self.is_fitted:
            raise ValueError("Modelo nao foi treinado. Use .fit() primeiro.")
        linear_model = np.dot(X, self.weights) + self.bias
        p1 = self.sigmoid(linear_model)
        return np.column_stack([1.0 - p1, p1])

    def predict(self, X):
        """Previsoes binarias (0 ou 1) com threshold 0.5."""
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)


class SimpleLinearRegression:
    """
    Regressao Linear com solucao analitica dos minimos quadrados.
    Fallback para gradient descent quando a matriz e singular — bug corrigido:
    o fallback nao chamava predict() antes de is_fitted=True.
    """

    def __init__(self):
        self.weights   = None
        self.bias      = None
        self.is_fitted = False

    def fit(self, X, y):
        """Treinar usando minimos quadrados; gradient descent como fallback."""
        n_samples, n_features = X.shape
        X_b = np.c_[np.ones((n_samples, 1)), X]   # adicionar coluna de bias

        try:
            # Solucao analitica: (X^T X)^-1 X^T y
            wb = np.linalg.inv(X_b.T.dot(X_b)).dot(X_b.T).dot(y)
            self.bias    = float(wb[0])
            self.weights = wb[1:]

        except np.linalg.LinAlgError:
            # Fallback: gradient descent
            # CORRECAO: calcular y_pred directamente sem chamar self.predict(),
            # pois is_fitted ainda e False neste ponto.
            self.weights = np.zeros(n_features)
            self.bias    = float(np.mean(y))
            lr           = 0.01

            for _ in range(1000):
                y_pred = np.dot(X, self.weights) + self.bias   # calculo directo
                erro   = y_pred - y
                dw     = (1.0 / n_samples) * np.dot(X.T, erro)
                db     = (1.0 / n_samples) * np.sum(erro)
                self.weights -= lr * dw
                self.bias    -= lr * db

        self.is_fitted = True
        return self

    def predict(self, X):
        """Fazer previsoes continuas."""
        if not self.is_fitted:
            raise ValueError("Modelo nao foi treinado. Use .fit() primeiro.")
        return np.dot(X, self.weights) + self.bias