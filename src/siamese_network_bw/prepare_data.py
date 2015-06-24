# Downloads the LFW (Labeled Faces in the Wild) dataset and converts it to an LMDB database for
# Caffe.

import shutil

import numpy as np
from sklearn.datasets import (
    fetch_lfw_pairs,
    fetch_lfw_people,
)
from sklearn.cross_validation import ShuffleSplit
import leveldb
from caffe_pb2 import Datum

import constants as constants
import siamese_network_bw.siamese_utils as siamese_utils

def prepare_data():
    print "Preparing data..."
    print "\tLoading LFW data..."

    # Each image is 47 (width) x 62 (height). There are 2200 training images, 6000 validation
    # images, and 1000 test images; note though that we change the split between training and
    # validation images later.
    train = {
        "file_path": constants.TRAINING_FILE,
        "lfw_pairs": fetch_lfw_pairs(subset="train")
    }
    validation = {
        "file_path": constants.VALIDATION_FILE,
        "lfw_pairs": fetch_lfw_pairs(subset="10_folds")
    }
    testing = {
        "file_path": constants.TESTING_FILE,
        "lfw_pairs": fetch_lfw_pairs(subset="test")
    }

    m, channels, height, width = testing["lfw_pairs"].pairs.shape

    testing["lfw_pairs"] = {
        "data": testing["lfw_pairs"].data,
        "target": testing["lfw_pairs"].target,
    }

    print "\tShuffling & combining data..."
    train, validation = prepare_training_validation_data(train, validation)

    for entry in [train, validation, testing]:
        generate_leveldb(entry["file_path"], entry["lfw_pairs"], channels, width, height)

    print "\tDone preparing data."

def prepare_training_validation_data(train, validation):
    """
    By default there is a strange split between the training and validation sets;
    the training set is 2200 images while the validation set is 6000 images. We'd rather
    have the split roughly the other way (80/20).
    """

    train_pairs = train["lfw_pairs"]
    validation_pairs = validation["lfw_pairs"]
    data = np.concatenate((train_pairs.data, validation_pairs.data))
    target = np.concatenate((train_pairs.target, validation_pairs.target))

    # After the split we should have 6560 training images and 1640 validation images.
    split = ShuffleSplit(n=len(data), train_size=0.8, test_size=0.2)

    for training_set, validation_set in split:
        X_train = data[training_set]
        y_train = target[training_set]

        X_validation = data[validation_set]
        y_validation = target[validation_set]

    train["lfw_pairs"] = {
        "data": X_train,
        "target": y_train
    }
    validation["lfw_pairs"] = {
        "data": X_validation,
        "target": y_validation
    }

    return (train, validation)

def generate_leveldb(file_path, lfw_pairs, channels, width, height):
    print "\tGenerating LevelDB file at %s..." % file_path
    shutil.rmtree(file_path, ignore_errors=True)
    db = leveldb.LevelDB(file_path)

    batch = leveldb.WriteBatch()
    # The 'data' entry contains both pairs of images unrolled into a linear vector.
    for idx, data in enumerate(lfw_pairs["data"]):
        # Each image pair is a top level key with a keyname like 00059999, in increasing
        # order starting from 00000000.
        key = siamese_utils.get_key(idx)
        print "\t\tPreparing key: %s" % key

        # Do things like mean normalize, etc. that happen across both testing and validation.
        data = preprocess_data(data)

        # Each entry in the leveldb is a Caffe protobuffer "Datum" object containing details.
        datum = Datum()
        # One channel for each image in the pair.
        datum.channels = channels
        datum.height = height
        datum.width = width
        # Our pixels are float values, such as -3.370285 after being mean normalized.
        datum.float_data.extend(data.astype(float).flat)
        datum.label = lfw_pairs["target"][idx]
        value = datum.SerializeToString()
        db.Put(key, value)

    db.Write(batch, sync = True)

def preprocess_data(data):
    """
    Applies any standard preprocessing we might do on data, whether it is during
    training or testing time. 'data' is a numpy array of unrolled pixel vectors with
    two side by side facial images for each entry.
    """
    data = siamese_utils.mean_normalize(data)

    # We don't scale it's values to be between 0 and 1 as our Caffe model will do that.

    return data

def prepare_testing_cluster_data():
    """
    Load individual faces for 5 different people, rather than pairs. These faces are known
    to have 10 or more images in the testing data.
    """
    print "\tLoading testing cluster data..."
    testing = fetch_lfw_people()
    data = testing["images"]
    labels = testing["target"]
    label_names = testing["target_names"]
    (m, height, width) = data.shape

    good_identities = [20, 52, 127, 210, 223]
    indexes_to_keep = [idx for idx in range(m) if labels[idx] in good_identities]
    data_to_keep = []
    labels_to_keep = []
    for i in range(len(indexes_to_keep)):
        keep_me_idx = indexes_to_keep[i]
        data_to_keep.append(data[keep_me_idx])
        labels_to_keep.append(labels[keep_me_idx])

    data_to_keep = np.array(data_to_keep)

    # Scale the data.
    caffe_in = data_to_keep.reshape(len(data_to_keep), 1, height, width) * 0.00392156
    caffe_in = preprocess_data(caffe_in)

    return (caffe_in, labels_to_keep, good_identities)
