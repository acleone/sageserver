if __name__ == '__main__':
    from sageserver.compnode.worker.worker import Worker
    w = Worker()
    w.loop()