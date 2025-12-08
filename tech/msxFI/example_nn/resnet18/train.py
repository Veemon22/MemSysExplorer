import torch
import torch.nn as nn
import torch.optim as optim
import torch.backends.cudnn as cudnn

import torchvision
import torchvision.transforms as transforms

import os
import argparse
from tqdm import tqdm

from model import ResNet18


class Trainer:
    """Handles the training and evaluation of a ResNet-18 model on CIFAR-10."""
    def __init__(self, config):
        self.config = config
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.best_acc = 0
        self.start_epoch = 0
        
        self._prepare_data()
        self._build_model()
        self._setup_optimizer()

    def _prepare_data(self):
        """Prepare CIFAR-10 dataset and dataloaders."""
        print('==> Preparing data..')
        transform_train = transforms.Compose([
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ])

        transform_test = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010)),
        ])

        trainset = torchvision.datasets.CIFAR10(
            root='./data', train=True, download=True, transform=transform_train)
        self.trainloader = torch.utils.data.DataLoader(
            trainset, batch_size=128, shuffle=True, num_workers=2)

        testset = torchvision.datasets.CIFAR10(
            root='./data', train=False, download=True, transform=transform_test)
        self.testloader = torch.utils.data.DataLoader(
            testset, batch_size=100, shuffle=False, num_workers=2)

    def _build_model(self):
        """Build the ResNet-18 model."""
        print('==> Building model..')
        self.net = ResNet18().to(self.device)
        if self.device == 'cuda':
            self.net = torch.nn.DataParallel(self.net)
            cudnn.benchmark = True

        if self.config.resume:
            self._load_checkpoint()

    def _load_checkpoint(self):
        """Load model from checkpoint."""
        print('==> Resuming from checkpoint..')
        checkpoint_dir = './checkpoints'
        if not os.path.isdir(checkpoint_dir):
            print('Error: no checkpoint directory found!')
            return
        
        checkpoint_path = os.path.join(checkpoint_dir, 'resnet18.pth')
        if not os.path.exists(checkpoint_path):
            print(f'Error: no checkpoint found at {checkpoint_path}!')
            return

        checkpoint = torch.load(checkpoint_path)
        self.net.load_state_dict(checkpoint['net'])
        self.best_acc = checkpoint['acc']
        self.start_epoch = checkpoint['epoch']
        print(f"Resumed from epoch {self.start_epoch} with accuracy {self.best_acc:.2f}%")

    def _setup_optimizer(self):
        """Setup the optimizer and learning rate scheduler."""
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.SGD(self.net.parameters(), lr=self.config.lr,
                                   momentum=0.9, weight_decay=5e-4)
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(self.optimizer, T_max=200)

    def train_epoch(self, epoch):
        """Train the model for one epoch."""
        print(f'\nEpoch: {epoch}')
        self.net.train()
        train_loss = 0
        correct = 0
        total = 0
        
        progress = tqdm(self.trainloader, desc='Training')
        for batch_idx, (inputs, targets) in enumerate(progress):
            inputs, targets = inputs.to(self.device), targets.to(self.device)
            self.optimizer.zero_grad()
            outputs = self.net(inputs)
            loss = self.criterion(outputs, targets)
            loss.backward()
            self.optimizer.step()

            train_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()

            progress.set_postfix({
                'Loss': f'{train_loss/(batch_idx+1):.3f}',
                'Acc': f'{100.*correct/total:.3f}% ({correct}/{total})'
            })
            
    def test_epoch(self, epoch):
        """Evaluate the model on the test set."""
        self.net.eval()
        test_loss = 0
        correct = 0
        total = 0
        
        progress = tqdm(self.testloader, desc='Testing')
        with torch.no_grad():
            for batch_idx, (inputs, targets) in enumerate(progress):
                inputs, targets = inputs.to(self.device), targets.to(self.device)
                outputs = self.net(inputs)
                loss = self.criterion(outputs, targets)

                test_loss += loss.item()
                _, predicted = outputs.max(1)
                total += targets.size(0)
                correct += predicted.eq(targets).sum().item()
                
                progress.set_postfix({
                    'Loss': f'{test_loss/(batch_idx+1):.3f}',
                    'Acc': f'{100.*correct/total:.3f}% ({correct}/{total})'
                })

        acc = 100. * correct / total
        if acc > self.best_acc:
            self._save_checkpoint(acc, epoch)

    def _save_checkpoint(self, acc, epoch):
        """Save the model checkpoint."""
        print('Saving checkpoint..')
        state = {
            'net': self.net.state_dict(),
            'acc': acc,
            'epoch': epoch,
        }
        checkpoint_dir = './checkpoints'
        if not os.path.isdir(checkpoint_dir):
            os.makedirs(checkpoint_dir)
        torch.save(state, os.path.join(checkpoint_dir, 'resnet18.pth'))
        self.best_acc = acc

    def run(self):
        """Start the training and evaluation loop."""
        for epoch in range(self.start_epoch, self.start_epoch + 200):
            self.train_epoch(epoch)
            self.test_epoch(epoch)
            self.scheduler.step()

def main():
    """Main function to run the training."""
    parser = argparse.ArgumentParser(description='PyTorch CIFAR-10 Training')
    parser.add_argument('--lr', default=0.1, type=float, help='learning rate')
    parser.add_argument('--resume', '-r', action='store_true',
                        help='resume from checkpoint')
    args = parser.parse_args()

    trainer = Trainer(args)
    trainer.run()

if __name__ == '__main__':
    main()