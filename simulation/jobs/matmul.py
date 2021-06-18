import numpy as np
import os

NUM_ITERATIONS: int = int(os.getenv("NUM_ITERATIONS", 30))


def main():
    # Basic matrix multiplication workload
    for i in range(NUM_ITERATIONS):
        print("Multiplication ", i)
        print(np.square(np.random.randint(10, size=(5000, 5000))))


if __name__ == '__main__':
    main()
