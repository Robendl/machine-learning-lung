import torch
import cv2
import numpy as np
from torch.utils.data import Dataset
from torch.utils.data import DataLoader
from PIL import Image
from network import *


class ImageDataset(Dataset):
    def __init__(self, indices):
        self.indices = indices

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, idx):
        #Load image
        image_path = "brain_tumour/test/images/" + str(idx) + ".png"
        image = cv2.imread(image_path, cv2.IMREAD_COLOR)

        #Load label
        label_path = "brain_tumour/test/masks/" + str(idx) + ".png"
        label = cv2.imread(label_path, cv2.IMREAD_GRAYSCALE) 

        image = cv2.resize(image, (512, 512))
        label = cv2.resize(label, (512, 512))

        image = image.astype(np.float32) / 255.0 
        label = label.astype(np.float32) / 255.0  
        image = torch.from_numpy(image)
        label = torch.from_numpy(label)
        
        return image, label


def f1_score(predicted, mask):
    predicted_flat = predicted.view(-1)  # flatten the predicted image
    mask_flat = mask.view(-1)  # flatten the mask
    TP = torch.sum(predicted_flat * mask_flat)  # true positives
    FP = torch.sum(predicted_flat) - TP  # false positives
    FN = torch.sum(mask_flat) - TP  # false negatives
    precision = TP / (TP + FP + 1e-7)  # precision
    recall = TP / (TP + FN + 1e-7)  # recall
    F1 = 2 * (precision * recall) / (precision + recall + 1e-7)  # F1 score
    return F1.item()  # convert tensor to scalar value


def test(model, image_indices):
    total_f1_score = 0

    test = ImageDataset(image_indices)
    test_set = DataLoader(test, batch_size=1, shuffle=True, num_workers=4)

    for idx, (image, label) in enumerate(test_set):
        with torch.no_grad():

            image = image.permute(0, 3, 1, 2)
            output = model(image.float().to('cuda'))
            label = label.float().to('cuda')
            
            output_binary = (output > 0.5).float()

            score = f1_score(output_binary, label)
            total_f1_score = total_f1_score + score

            output_binary = output_binary.squeeze()  
            output_binary = output_binary.detach().cpu().numpy()
            output_image = Image.fromarray((output_binary * 255).astype(np.uint8))
            output_image = output_image.convert("L")
            output_image.save('results/tensor_image' + str(idx) + '.png')

            label_binary = label.squeeze()  
            label_binary = label_binary.detach().cpu().numpy()
            output_image = Image.fromarray((label_binary * 255).astype(np.uint8))
            output_image = output_image.convert("L")
            output_image.save('results/mask' + str(idx) + '.png')

    total_f1_score = total_f1_score / 307

    print("mean f1 score", total_f1_score)
    return total_f1_score


if __name__ == '__main__':
    model = UnetWithHeader(n_channels=3, n_classes=1, mode="mlp")
    model = model.cuda()

    state_dict = torch.load("results/unet.pth", map_location=torch.device('cuda:0'))
    model.load_state_dict(state_dict, strict=True)
    image_indices = list(range(0, 307))
    test(model, image_indices)
