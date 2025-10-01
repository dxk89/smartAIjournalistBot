# File: src/my_framework/style_guru/model.py

import numpy as np

class AdvancedNeuralAgent:
    """
    NN for IntelliNews style scoring.
    Input: feature vector (text style metrics)
    Output: scalar style score
    """

    def __init__(self, input_size: int, hidden=[64, 32], lr=1e-3):
        self.lr = lr
        self.layers = []
        layer_sizes = [input_size] + hidden + [1]
        for i in range(len(layer_sizes)-1):
            fan_in, fan_out = layer_sizes[i], layer_sizes[i+1]
            limit = np.sqrt(6.0 / (fan_in + fan_out))
            self.layers.append({
                "w": np.random.uniform(-limit, limit, (fan_in, fan_out)),
                "b": np.zeros((1, fan_out)),
                "mw": np.zeros((fan_in, fan_out)),
                "mb": np.zeros((1, fan_out)),
            })

    def _relu(self, x): return np.maximum(0, x)
    def _drelu(self, x): return (x > 0).astype(float)

    def forward(self, X):
        self.a = [X]; self.z = []
        for i, l in enumerate(self.layers):
            z = np.dot(self.a[-1], l["w"]) + l["b"]
            self.z.append(z)
            if i < len(self.layers)-1:
                self.a.append(self._relu(z))
            else:
                self.a.append(z)  # linear output
        return self.a[-1]

    def train(self, X, y, epochs=100, batch_size=16):
        y = y.reshape(-1, 1)
        for ep in range(epochs):
            idx = np.random.permutation(len(X))
            Xs, ys = X[idx], y[idx]
            losses = []
            for i in range(0, len(Xs), batch_size):
                xb, yb = Xs[i:i+batch_size], ys[i:i+batch_size]
                out = self.forward(xb)
                dz = (out - yb) / len(xb)
                for li in reversed(range(len(self.layers))):
                    l = self.layers[li]
                    a_prev = self.a[li]
                    dw = np.dot(a_prev.T, dz)
                    db = np.sum(dz, axis=0, keepdims=True)
                    l["w"] -= self.lr * dw
                    l["b"] -= self.lr * db
                    if li > 0:
                        dz = np.dot(dz, l["w"].T) * self._drelu(self.z[li-1])
                losses.append(np.mean((out - yb)**2))
            if ep % 10 == 0:
                print(f"Epoch {ep}: loss {np.mean(losses):.4f}")

    def predict(self, X):
        return self.forward(X)

    def save(self, path="data/model_weights.npz"):
        np.savez(path, **{f"w{i}": l["w"] for i,l in enumerate(self.layers)},
                        **{f"b{i}": l["b"] for i,l in enumerate(self.layers)})

    def load(self, path="data/model_weights.npz"):
        data = np.load(path)
        for i,l in enumerate(self.layers):
            l["w"] = data[f"w{i}"]
            l["b"] = data[f"b{i}"]