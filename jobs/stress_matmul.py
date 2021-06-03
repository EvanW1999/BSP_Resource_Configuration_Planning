import subprocess


def main() -> None:
    """This job will run stress-ng benchmark and wait for commands
    from a Redis queue.
    """
    output: str = subprocess.check_output(
        ["stress-ng", "--matrix", "0", "--metrics", "--cpu-ops", str(50000), "-t", "1m"])
    print(output)


if __name__ == '__main__':
    main()
