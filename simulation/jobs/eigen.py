import numpy as np

import os

NUM_ITERATIONS: int = int(os.getenv("NUM_ITERATIONS", 30))


def main():
    for i in range(NUM_ITERATIONS):
        print("Eigendecomposition", i)
        print(np.linalg.eig(np.random.randint(10, size=(500, 500))))


if __name__ == '__main__':
    main()
