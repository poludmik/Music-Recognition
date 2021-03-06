import numpy as np
import seaborn as sn
from dataset import songsDS
from model import NeuralNetModel
import torch
import torch.nn as nn
import pandas as pd
import matplotlib.pyplot as plt



class TrainingAssistant:

    # Labels for GTZAN dateset:
    # label_dictionary = {0: "blues", 1: "classical", 2: "country", 3: "disco",
    #       4: "hiphop", 5: "jazz", 6: "metal", 7: "pop", 8: "reggae", 9: "rock"}

    # Labels for my custom dataset:
    label_dictionary = {0: "classical", 1: "pop", 2: "rap", 3: "lofi", 4: "metal"}

    @staticmethod
    def plot_train_and_val_losses(tr_losses, vl_losses, epoch_number):
        """
        Method to show the loss progression during epochs using matplotlib.

        :param list tr_losses: A list of float losses obtained from training data during training.
        :param list vl_losses: A list of float losses obtained from validation data during training.
        :param int epoch_number: Current number of epochs.
        """
        epoch_list = list(range(0, epoch_number + 1))
        plt.style.use('seaborn-whitegrid')
        plt.plot(epoch_list, tr_losses, '-b', label='train loss')
        plt.plot(epoch_list, vl_losses, '-r', label='val loss')
        plt.legend(loc="upper right")
        plt.xlabel("Epoch number")
        plt.ylabel("Average CrossEntropyLoss")
        plt.suptitle("Train and Val loss progression")
        plt.show()
        plt.rcParams.update(plt.rcParamsDefault)

    @staticmethod
    def plot_confusion_matrix(conf_matrix):
        """
        Method to show the obtained confusion matrix using matplotlib.

        :param conf_matrix: A 2D confusion list with prediction axis and label axis.
        """
        df_cm = pd.DataFrame(conf_matrix, index=[i for i in "01234"],
                             columns=[i for i in "01234"])
        fig = plt.figure(figsize=(10, 7))
        fig.suptitle("Confusion matrix of test songs.", fontsize=20)
        plt.title(r"0: classical, 1: pop, 2: rap, 3: lofi, 4: metal", fontsize=15)
        sn.heatmap(df_cm, annot=True, cmap="GnBu")
        plt.xlabel("Predictions", fontsize=18)
        plt.ylabel("True genres", fontsize=18)
        plt.show()
        plt.rcParams.update(plt.rcParamsDefault)

    @staticmethod
    def train(weights_path=None, batch_size=16, lr=0.001, epochs=50, save_dir=None):
        """
        Main training loop, here NN improves provided weights or creates new ones.
        Stores achieved weights into save_dir, if provided.

        :param str weights_path: Absolute path to weights or None to start new learning.
        :param int batch_size: Batch size to be used in forward pass.
        :param float lr: Learning rate.
        :param int epochs: Number of epochs to be executed.
        :param str save_dir: Absolute path determining where to store achieved weights, None = do not store.
        """
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # print(device)

        if not isinstance(save_dir, str):
            print("Directionary for saving weights is None.")

        lr = lr
        batch_size = batch_size
        epochs = epochs

        trainDS = songsDS(train=True)
        valDS = songsDS(validate=True)

        # Create training and validation data loaders
        trainDL = torch.utils.data.DataLoader(trainDS, batch_size=batch_size, shuffle=True)
        valDL = torch.utils.data.DataLoader(valDS, batch_size=batch_size, shuffle=False)

        model = NeuralNetModel()
        model.to(device)
        if isinstance(weights_path, str):
            model.load_state_dict(torch.load(weights_path))

        loss_criterium = nn.CrossEntropyLoss()  # CrossEntropyLoss is for predictions of probabilities, in range [0, 1]

        optimizer = torch.optim.Adam(model.parameters(), lr=lr)

        train_losses = []
        val_losses = []

        min_loss = 666


        for epoch in range(epochs):

            confusion_matrix = [([0] * 5) for i in range(5)]

            sum_of_train_losses = sum_of_val_losses = 0

            for data in trainDL:
                # data[0] is a batch of batch_size spectograms-tensors of shape [1, 90, 260]
                # data[1] is a batch of corresponding labels, e.g. tensor([5, 7, 8, 1, 3, 8, 0, 5, 0, 7, 9, 6, 5, 8, 4, 1])
                images, labels = data
                images = images.to(device)
                labels = labels.to(device)

                # standartization
                # images = (images - torch.mean(images)) / torch.std(images)

                predictions = model(images)

                # print(predictions, labels)
                loss = loss_criterium(predictions, labels)

                sum_of_train_losses += loss.item()

                # Do the backward pass and update the gradients
                loss.backward()
                optimizer.step()
                optimizer.zero_grad()

            for data in valDL:
                images, labels = data
                images = images.to(device)
                labels = labels.to(device)

                predictions = model(images)
                loss = loss_criterium(predictions, labels)
                sum_of_val_losses += loss.item()
                optimizer.zero_grad()

            mean_train_loss = sum_of_train_losses / (trainDS.length // batch_size)
            train_losses.append(mean_train_loss)

            mean_val_loss = sum_of_val_losses / (valDS.length // batch_size)
            val_losses.append(mean_val_loss)

            print("Ep:%d, Mean train loss:%.4f, Mean val loss:%.4f." % (epoch, mean_train_loss, mean_val_loss))
            TrainingAssistant.plot_train_and_val_losses(train_losses, val_losses, epoch_number=epoch)

            if min_loss > mean_val_loss and isinstance(save_dir, str):
                torch.save(model.state_dict(), save_dir + "/weights_myDataset_test_Ep" + str(epoch) + "_loss" + str(mean_val_loss) + ".pth")
                min_loss = mean_val_loss

            TrainingAssistant.plot_confusion_matrix(confusion_matrix)


    @staticmethod
    def test_on_custom_audio(weights_dir):
        """
        Method does forward pass of all the audio tracks in the testing folder, which is specified in dataset.py
        It outputs the predictions about each track and creates a confusion matrix based on a "testing_labels.csv".
        Method is used to test the neural network weights which were obtained during the training.

        :param str weights_dir: Absolute path to weights that need to be tested.
        """
        if weights_dir is None:
            print("No weights path given.")
            return

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        testDS = songsDS(test=True)
        testDL = torch.utils.data.DataLoader(testDS, batch_size=1, shuffle=True)
        model = NeuralNetModel()
        model.to(device)
        model.load_state_dict(torch.load(weights_dir))

        confusion_matrix = [([0] * 5) for i in range(5)]

        for data in testDL:
            image, label = data
            image = image.to(device)

            predictions = model(image)

            for i, prediction in enumerate(predictions):
                n = np.array(prediction.tolist())
                index = np.argmax(n)
                confusion_matrix[int(torch.nan_to_num(label)[0])][index] += 1

            n = np.array(predictions.tolist())
            index = np.argmax(n)

            for i, probability in enumerate(predictions.tolist()[0]):
                print("%9s = %.5f" % (TrainingAssistant.label_dictionary[i], probability))

            print(f'Argmax index is: {index}, which is {TrainingAssistant.label_dictionary[index]}.\n')

        TrainingAssistant.plot_confusion_matrix(confusion_matrix)



if __name__ == "__main__":

    weights = "C:/Users/micha/homeworks/personal/Music/data/mishas_custom_dataset/weights/weights_myDataset_Ep68_loss1.1222665111223857.pth"
    TrainingAssistant.test_on_custom_audio(weights)

    """
    # weights = None
    weights = "C:/Users/micha/homeworks/personal/Music/data/mishas_custom_dataset/weights/weights_myDataset_Ep68_loss1.1222665111223857.pth"
    save_directionary = "C:/Users/micha/homeworks/personal/Music/data/mishas_custom_dataset/weights"

    TrainingAssistant.train(weights_path=weights,
                            batch_size=16,
                            lr=0.001,
                            epochs=70,
                            save_dir=save_directionary)
    """














