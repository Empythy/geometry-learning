"""
This script executes the task of estimating the number of inhabitants of a neighborhood to be under or over the
median of all neighborhoods, based solely on the geometry for that neighborhood. The data for this script can be
generated by running the prep/get-data.sh and prep/preprocess-neighborhoods.py scripts, which will take about an hour
or two.

This script itself will run for about twelve seconds depending on your hardware, if you have at least a recent i7 or
comparable.
"""

import multiprocessing
import os
import sys
from datetime import datetime, timedelta
from time import time

import numpy as np
from sklearn.metrics import accuracy_score
from sklearn.model_selection import StratifiedShuffleSplit, GridSearchCV, cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from topoml_util.slack_send import notify

SCRIPT_VERSION = '1.0.3'
SCRIPT_NAME = os.path.basename(__file__)
TIMESTAMP = str(datetime.now()).replace(':', '.')
TRAINING_DATA_FILE = '../../files/neighborhoods/neighborhoods_train.npz'
REPEAT_ACCURACY_TEST = 10
NUM_CPUS = multiprocessing.cpu_count() - 1 if multiprocessing.cpu_count() > 1 else 1
SCRIPT_START = time()

if __name__ == '__main__':  # this is to squelch warnings on scikit-learn multithreaded grid search
    train_loaded = np.load(TRAINING_DATA_FILE)
    train_fourier_descriptors = train_loaded['fourier_descriptors']
    train_labels = train_loaded['above_or_below_median']

    scaler = StandardScaler().fit(train_fourier_descriptors)
    train_fourier_descriptors = scaler.transform(train_fourier_descriptors)
    clf = DecisionTreeClassifier()

    param_grid = {'max_depth': range(4, 10)}
    cv = StratifiedShuffleSplit(n_splits=5, test_size=0.2, random_state=42)
    grid = GridSearchCV(
        DecisionTreeClassifier(),
        n_jobs=NUM_CPUS,
        param_grid=param_grid,
        verbose=10,
        cv=cv)

    print('Performing grid search on model...')
    print('Using %i threads for grid search' % NUM_CPUS)
    grid.fit(train_fourier_descriptors, train_labels)
    print("The best parameters are %s with a score of %0.3f"
          % (grid.best_params_, grid.best_score_))

    print('Training model on best parameters...')
    clf = DecisionTreeClassifier(max_depth=grid.best_params_['max_depth'])
    clf.fit(train_fourier_descriptors, train_labels)

    scores = cross_val_score(clf, train_fourier_descriptors, train_labels, cv=10, n_jobs=NUM_CPUS)
    print('Cross-validation scores:', scores)

    # Run predictions on unseen test data to verify generalization
    TEST_DATA_FILE = '../../files/neighborhoods/neighborhoods_test.npz'
    test_loaded = np.load(TEST_DATA_FILE)
    test_fourier_descriptors = test_loaded['fourier_descriptors']
    test_labels = np.asarray(test_loaded['above_or_below_median'], dtype=int)
    test_fourier_descriptors = scaler.transform(test_fourier_descriptors)

    print('Run on test data...')
    predictions = clf.predict(test_fourier_descriptors)
    test_accuracy = accuracy_score(test_labels, predictions)
    print('Test accuracy: %0.3f' % test_accuracy)

    # Repeat on all data to assess spread in model accuracy from random splits
    print('Running random split accuracy spread test...')
    train_fourier_descriptors = np.append(train_fourier_descriptors, test_fourier_descriptors, axis=0)
    train_labels = np.append(train_labels, test_labels, axis=0)

    accuracy_scores = []

    for _ in range(REPEAT_ACCURACY_TEST):
        train_fourier_descriptors, test_fourier_descriptors, train_labels, test_labels = \
            train_test_split(train_fourier_descriptors, train_labels, test_size=0.1)
        grid.fit(train_fourier_descriptors, train_labels)
        print("The best parameters are %s with a score of %0.3f" % (grid.best_params_, grid.best_score_))
        print('Training model on best parameters...')
        clf = DecisionTreeClassifier(max_depth=grid.best_params_['max_depth'])
        clf.fit(train_fourier_descriptors, train_labels)
        print('Run on test data...')
        predictions = clf.predict(test_fourier_descriptors)
        accuracy = accuracy_score(test_labels, predictions)
        accuracy_scores.append(accuracy)

    runtime = time() - SCRIPT_START
    print('')
    message = 'test accuracy of {} with standard deviation {} in {}'.format(
        test_accuracy, np.std(accuracy_scores), timedelta(seconds=runtime))
    print(message)
    print('Random split accuracy values: {}'.format(accuracy_scores))

    notify(SCRIPT_NAME, message)
    print(SCRIPT_NAME, 'finished successfully')
