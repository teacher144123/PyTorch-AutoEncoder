import time, os
import torch
from torch.optim.lr_scheduler import StepLR
import torch.nn.functional as F
from torchvision.utils import save_image

from tqdm import tqdm
import matplotlib.pyplot as plt
# 
from dataset import get_dataset
from model import ConvAutoEncoder

def train(model, data, epoch, criterion, optimizer, device):
    model.train()
    print('==========Train Epoch {}=========='.format(epoch))
    loss_list = []

    for i, (image, _) in tqdm(enumerate(data), total=len(data)):
#         image = image.view(image.size(0), -1).to(device)
        image = image.to(device)

        optimizer.zero_grad()
        recon = model(image)
        
        loss = criterion(recon, image)
        loss_list.append(loss.item())
        loss.backward()  # back-propagation
        optimizer.step() # gradient descent

    return sum(loss_list) / len(loss_list)

def test(model, data, criterion, device):
    model.eval()
    loss_list = []

    for i, (image, _) in tqdm(enumerate(data), total=len(data)):
#         image = image.view(image.size(0), -1).to(device)
        image = image.to(device)

        recon = model(image)
        loss = criterion(recon, image)
        loss_list.append(loss.item())
    
        if i == 0 and epoch % 5 == 0:
            n = min(image.size(0), 8)
            comparison = torch.cat([image.view(-1, 1, 28, 28)[:n],
                                  recon.view(-1, 1, 28, 28)[:n]])
            save_image(comparison.cpu(),
                     'results/recon_{:03}.png'.format(epoch), nrow=n)

    return sum(loss_list) / len(loss_list)

if __name__ == '__main__':
    # == Setting ==
    device = torch.device('cuda')
    print('Using', device)
    
    # == Data ==
    data_name = 'mnist'
    print('Data using: {}'.format(data_name))
    train_data, test_data = get_dataset(data_name)
    
    
    # make dirs
    os.makedirs('results', exist_ok=True)
    os.makedirs('ckpts', exist_ok=True)

    # == Model ==
    model = ConvAutoEncoder().to(device)

    # == optimizer ==
    criterion = torch.nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.0001)

    # == Main Loop ==
    max_acc = 0
    max_epoch = 50
#     scheduler = StepLR(optimizer=optimizer, step_size=10)

    # first epoch
    # test(model, test_data, device=device)
    train_loss_list = []
    test_loss_list = []

    for epoch in range(1, max_epoch + 1):
        t = time.time()
        train_loss = train(model, train_data, epoch, criterion, optimizer, device=device)
        test_loss = test(model, test_data, criterion, device=device)
#         scheduler.step()

        print('train loss:', train_loss, 'test loss:', test_loss)

        train_loss_list.append(train_loss)
        test_loss_list.append(test_loss)

        print('Epoch {} cost {} sec'.format(epoch, time.time() - t))
        t = time.time()

        plt.plot(range(1, epoch + 1), train_loss_list)
        plt.plot(range(1, epoch + 1), test_loss_list, color='r')
        plt.legend(['train_loss', 'test_loss'])
        plt.savefig('{}_ae_loss.png'.format(data_name))
        plt.cla()
        
        if epoch % 5 == 0:
            print('----- epoch {} -----'.format(epoch))
            torch.save(model.state_dict(), 'ckpts/e{:03}ae_{}.pt'.format(
                epoch, data_name))
            
            # sample
            sample = torch.randn(64, 128).to(device)
            sample = model.decoder(sample).cpu()
            save_image(sample.view(64, 1, 28, 28),
                       'results/sample_e{:02}.png'.format(epoch))