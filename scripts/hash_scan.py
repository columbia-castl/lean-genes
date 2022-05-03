import hashlib, random, time

num_hashes = 1000000
num_samples = 10

linear_hash_array = [] 
samples = []
sample_indices = []
times = []

def populate_array():
    for i in range(num_hashes):
        linear_hash_array.append(hashlib.sha3_256(str(i).encode()))
    print("hash array populated")

def sample_array():
    for i in range(num_samples):
        rand_index = random.randint(0, num_hashes - 1)
        samples.append(linear_hash_array[rand_index])
        sample_indices.append(rand_index)
    print("array sampled")

def time_sample(sample_index):

    array_index = sample_indices[sample_index]
    hash = samples[sample_index]
    found = False
    ind = 0

    time1 = time.time()
    while not found:
        if linear_hash_array[ind] != hash:
            ind += 1
        else:
            found = True
        if ind > num_hashes:
            print("Error: didn't find hash")
    time2 = time.time()

    return (time2 - time1)


def main():
    populate_array()
    sample_array()

    for i in range(num_samples):
        time = time_sample(i)
        times.append(time)

    for i in range(num_samples):
        print("index " + str(sample_indices[i]) + " --- " + str(times[i]) + " s")
        


if __name__ == '__main__':
    main()