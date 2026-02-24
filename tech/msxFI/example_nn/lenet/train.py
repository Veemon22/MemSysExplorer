import torch
import torch.nn as nn
import torch.optim as optim
from model import LeNet
import os
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

datasets.MNIST.mirrors = ['https://ossci-datasets.s3.amazonaws.com/mnist/']

EPOCHS = 5 
LR = 0.001
BATCH_SIZE = 64
DATA_ROOT = './data'
MODEL_SAVE_DIR = './checkpoints' 
MODEL_SAVE_NAME = 'lenet.pth'

def get_mnist_dataloaders(batch_size, train_root='./data', download=True, test_batch_size=None, shuffle_train=True, shuffle_test=False):
    if test_batch_size is None:
        test_batch_size = batch_size

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,)) 
    ])

    train_dataset = datasets.MNIST(
        root=train_root,
        train=True,
        download=download,
        transform=transform
    )
    train_loader = DataLoader(
        dataset=train_dataset,
        batch_size=batch_size,
        shuffle=shuffle_train
    )

    test_dataset = datasets.MNIST(
        root=train_root,
        train=False,
        download=download,
        transform=transform
    )
    test_loader = DataLoader(
        dataset=test_dataset,
        batch_size=test_batch_size,
        shuffle=shuffle_test
    )

    return train_loader, test_loader 

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    print(f"Loading MNIST data. Data will be stored/loaded from: {os.path.abspath(DATA_ROOT)}")
    train_loader, test_loader = get_mnist_dataloaders(BATCH_SIZE, train_root=DATA_ROOT, download=True)

    model = LeNet(num_classes=10).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LR)

    print("Starting training with LeNet...")
    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        for i, (inputs, labels) in enumerate(train_loader):
            inputs, labels = inputs.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item()
            if (i + 1) % 100 == 0:
                print(f'Epoch [{epoch+1}/{EPOCHS}], Step [{i+1}/{len(train_loader)}], Loss: {running_loss / 100:.4f}')
                running_loss = 0.0
        
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for images, labels in test_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
        accuracy = 100 * correct / total
        print(f'Epoch [{epoch+1}/{EPOCHS}] Test Accuracy: {accuracy:.2f}%')

    print("Finished training.")

    model_save_path = os.path.join(MODEL_SAVE_DIR, MODEL_SAVE_NAME)
    os.makedirs(MODEL_SAVE_DIR, exist_ok=True)
    torch.save(model, model_save_path)
    print(f"Trained LeNet model saved to {os.path.abspath(model_save_path)}")

if __name__ == "__main__":
    main() 