import numpy as np


def main():
    # Basic matrix multiplication workload
    for i in range(30):
        print("Multiplication ", i)
        print(np.square(np.random.randint(10, size=(5000, 5000))))


if __name__ == '__main__':
    main()
