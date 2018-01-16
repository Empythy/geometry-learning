"""
This script executes the task of estimating the building type, based solely on the geometry signature for that
neighborhood. The data for this script can be generated by running the prep/get-data.sh and
prep/preprocess-buildings.py scripts, which will take about an hour or two.

The script itself will run for about two hours depending on your hardware, if you have at least a recent i7 or
comparable
"""

import os
import sys
import multiprocessing
from datetime import datetime

import numpy as np
from sklearn.model_selection import StratifiedShuffleSplit, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

from topoml_util.slack_send import notify

SCRIPT_VERSION = '0.0.4'
SCRIPT_NAME = os.path.basename(__file__)
TIMESTAMP = str(datetime.now()).replace(':', '.')
DATA_FOLDER = SCRIPT_DIR + '/../../files/buildings/'
FILENAME_PREFIX = 'buildings-train'
NUM_CPUS = multiprocessing.cpu_count() - 1 or 1

if __name__ == '__main__':  # this is to squelch warnings on scikit-learn multithreaded grid search
    # Load training data
    training_files = []
    for file in os.listdir(DATA_FOLDER):
        if file.startswith(FILENAME_PREFIX) and file.endswith('.npz'):
            training_files.append(file)

    train_fourier_descriptors = np.array([])
    train_building_type = np.array([])

    for index, file in enumerate(training_files):  # load and concatenate the training files
        train_loaded = np.load(DATA_FOLDER + file)

        if index == 0:
            train_fourier_descriptors = train_loaded['fourier_descriptors']
            train_building_type = train_loaded['building_type']
        else:
            train_fourier_descriptors = \
                np.append(train_fourier_descriptors, train_loaded['fourier_descriptors'], axis=0)
            train_building_type = \
                np.append(train_building_type, train_loaded['building_type'], axis=0)

    scaler = StandardScaler().fit(train_fourier_descriptors)
    train_fourier_descriptors = scaler.transform(train_fourier_descriptors)

    C_range = [1e-3, 1e-2, 1e-1, 1e0, 1e1]
    gamma_range = np.logspace(-9, 3, 13)
    param_grid = dict(gamma=gamma_range, C=C_range)
    cv = StratifiedShuffleSplit(n_splits=5, test_size=0.2, random_state=42)
    grid = GridSearchCV(
        SVC(kernel='rbf', verbose=True, max_iter=int(1e7)),
        n_jobs=NUM_CPUS,
        param_grid=param_grid, cv=cv)

    print('Performing grid search on model...')
    print('Using %i threads for grid search' % NUM_CPUS)
    grid.fit(X=train_fourier_descriptors, y=train_building_type)

    print("The best parameters are %s with a score of %0.2f"
          % (grid.best_params_, grid.best_score_))

    clf = SVC(kernel='rbf', C=grid.best_params_['C'], gamma=grid.best_params_['gamma'], verbose=True)
    clf.fit(X=train_fourier_descriptors, y=train_building_type)

    # Run predictions on unseen test data to verify generalization
    print('Run on test data...')
    TEST_DATA_FILE = '../files/buildings/buildings-test.npz'
    test_loaded = np.load(TEST_DATA_FILE)
    test_fourier_descriptors = test_loaded['fourier_descriptors']
    test_building_type = np.asarray(test_loaded['building_type'], dtype=int)
    test_fourier_descriptors = scaler.transform(test_fourier_descriptors)

    predictions = clf.predict(test_fourier_descriptors)

    correct = 0
    for prediction, expected in zip(predictions, test_building_type):
        if prediction == expected:
            correct += 1

    accuracy = correct / len(predictions)
    print('Test accuracy: %0.2f' % accuracy)

    message = 'test accuracy of {0} with ' \
              'C: {1} ' \
              'gamma: {2} ' \
        .format(
            str(accuracy),
            grid.best_params_['C'],
            grid.best_params_['gamma'],
        )
    notify(SCRIPT_NAME, message)
    print(SCRIPT_NAME, 'finished successfully')
