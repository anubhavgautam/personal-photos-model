import matplotlib.pyplot as plt
from sklearn.datasets import fetch_lfw_people
import numpy as np
import caffe

import constants as constants
import prepare_data as prepare_data
import siamese_network_bw.siamese_utils as siamese_utils

def predict(img_1, img_2):
    print "Predicting..."
    # TODO!!! Implement!!!

def test_clusters(data=None, weight_file=constants.TRAINED_WEIGHTS):
    """
    Tests a few people to see how they cluster across the training and validation data, producing
    image files.
    """
    print "Generating cluster details..."
    cluster_details = data.get_clustered_faces()

    print "\tInitializing Caffe using weight file %s..." % (weight_file)
    caffe.set_mode_cpu()
    net = caffe.Net(constants.TRAINED_MODEL, weight_file, caffe.TEST)

    test_cluster(net, cluster_details["train"], "train")
    test_cluster(net, cluster_details["validation"], "validation")

def test_cluster(net, cluster_details, graph_name):
    """
    Actually tests the cluster on the network for a given data set, generating a graph.
    """
    data = cluster_details["data"]
    target = cluster_details["target"]
    good_identities = cluster_details["good_identities"]

    print "\tRunning through network to generate cluster prediction for %s dataset..." % graph_name
    out = net.forward_all(data=data)

    print "\tGraphing..."
    feat = out["feat"]
    f = plt.figure(figsize=(16,9))
    c = {
      str(good_identities[0]): "#ff0000",
      str(good_identities[1]): "#ffff00",
      str(good_identities[2]): "#00ff00",
      str(good_identities[3]): "#00ffff",
      str(good_identities[4]): "#0000ff",
    }
    for i in range(len(feat)):
      plt.plot(feat[i, 0], feat[i, 1], ".", c=c[str(target[i])])
    plt.grid()

    plt.savefig(constants.get_output_cluster_path(graph_name))
    print("\t\tGraph saved to %s" % constants.get_output_cluster_path(graph_name))
