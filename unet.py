import torch
import torch.nn as nn
import cv2
import numpy as np
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
import torch.optim as optim
from augmentations import *
from network import *


class ImageDataset(Dataset):
    def __init__(self, indices, image_indices, transform=False):
        self.indices = indices
        self.transform = transform
        self.image_indices = image_indices

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, idx):
        random_img_number = self.image_indices[idx]

        #Load image
        image_path = "brain_tumour/train/lab_images/" + str(random_img_number) + ".png"
        image = cv2.imread(image_path, cv2.IMREAD_COLOR)

        #Load label
        label_path = "brain_tumour/train/masks/" + str(random_img_number) + ".png"
        label = cv2.imread(label_path, cv2.IMREAD_GRAYSCALE) 

        image = cv2.resize(image, (512, 512))
        label = cv2.resize(label, (512, 512))

        if self.transform:
            image, label = perform_augmentations(image, label)

        image = image.astype(np.float32) / 255.0 
        label = label.astype(np.float32) / 255.0  
        image = torch.from_numpy(image)
        label = torch.from_numpy(label)
        
        return image, label


def bce_loss(y_pred, y_true):
    func = nn.BCEWithLogitsLoss()
    return func(y_pred.squeeze(), y_true.float().to('cuda'))


def dice_loss(y_pred, y_true):
    y_pred = torch.sigmoid(y_pred).squeeze()
    y_true = y_true.float().to('cuda')

    smooth = 1e-5
    y_true = y_true.view(-1, 512, 512)
    y_pred = y_pred.view(-1, 512, 512)
    intersection = torch.sum(y_true * y_pred)
    sum_ = torch.sum(y_true + y_pred)
    dice = (2. * intersection + smooth) / (sum_ + smooth)
    return 1. - dice


def combined_loss(y_pred, y_true):
    return dice_loss(y_pred, y_true) + bce_loss(y_pred, y_true)


def validate(dataloader_valset, model, loss_function):
    model.eval()
    # validation steps
    with torch.no_grad():

        valid_loss = 0.0
        counter = 0

        for (images, labels) in dataloader_valset:
            images = images.permute(0, 3, 1, 2)
            output = model(images.float().to('cuda'))
                
            loss = loss_function(output, labels)
            valid_loss += loss.item()
            counter += 1
            
        valid_loss /= counter
    
    return valid_loss


def save_model(model, save_file):
    torch.save(model.state_dict(), save_file)


def load_path(model, path):
    print('path:\t', path)
    state_dict = torch.load(path, map_location=torch.device('cuda:0'))
    
    print("model before", model.state_dict()['unet.down1.conv.0.weight'][0][0][0])
    model.load_state_dict(state_dict, strict=False)

    print("model after", model.state_dict()['unet.down1.conv.0.weight'][0][0][0])
    return model


def train(model, image_indices, learning_rate=0.00001, loss_function=combined_loss, num_epochs=30, batch_size=8):
    random.shuffle(image_indices)

    train_dataset = ImageDataset(image_indices, image_indices, True)
    dataloader_trainset = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4)

    optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=10e-6)

    for epoch in range(num_epochs):
        model.train()
        total_loss = 0.0
        batch_counter = 1

        for (images, labels) in dataloader_trainset:
            optimizer.zero_grad()

            images = images.permute(0, 3, 1, 2)
            output = model(images.float().to('cuda'))

            loss = loss_function(output, labels)

            loss.backward()
            optimizer.step()
            batch_counter += 1
            total_loss += loss.item()

        total_loss /= batch_counter

        print("EPOCH: ", int(epoch))
        print("train loss", total_loss)


if __name__ == '__main__':
    model = UnetWithHeader(n_channels=3, n_classes=1, mode="mlp")
    model = model.cuda()
    image_indices = list(range(0,551))
    train(model, image_indices)
