import time
import torch
from torch.optim.lr_scheduler import StepLR
import torch.nn.functional as F
from torchvision.utils import save_image

from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy as np
# 
from dataset import get_dataset
from model import VAE

def train(model, data, epoch, criterion, optimizer, device):
    model.train()
    print('==========Train Epoch {}=========='.format(epoch))
    loss_list = []

    for i, (image, _) in tqdm(enumerate(data), total=len(data)):
        image = image.to(device)

        optimizer.zero_grad()
        recon, mu, logvar = model(image)
        
        loss, bce_loss, kld_loss = criterion(recon, image, mu, logvar) # calculate error
        if i == 0:
            print('bce', bce_loss, 'kld', kld_loss)
#         loss = criterion(recon, image)
        loss_list.append(loss.item())
        loss.backward()  # back-propagation
        optimizer.step() # gradient descent

    return sum(loss_list) / len(loss_list)

def test(model, data, criterion, device):
    model.eval()
    loss_list = []

    for i, (image, _) in tqdm(enumerate(data), total=len(data)):
        image = image.to(device)

        recon, mu, logvar = model(image)
        loss, _, _ = criterion(recon, image, mu, logvar)
#         loss = criterion(recon, image)
        loss_list.append(loss.item())
    
        if i == 0 and epoch % 5 == 0:
            n = min(image.size(0), 16)
            comparison = torch.cat([image[:n],
                                  recon.view(-1, 1, 28, 28)[:n]])
            save_image(comparison.cpu(),
                     'results/recon_{:03}.png'.format(epoch), nrow=n)

    return sum(loss_list) / len(loss_list)

def bce_kld_loss(recon_x, x, mu, logvar):
    # bce_loss = torch.mean(F.bce_loss(recon_x, x.view(-1, 784)))
    bce_loss = F.binary_cross_entropy(recon_x, x.view(-1, 784), reduction='sum')
    
    kld_loss = torch.mean(-0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp(), dim=1), dim=0)
    return bce_loss + kld_loss, bce_loss.item(), kld_loss.item()

if __name__ == '__main__':
    # == Setting ==
    device = torch.device('cuda')
    print('Using', device)
    
    # == Data ==
    data_name = 'mnist'
    print('Data using: {}'.format(data_name))
    train_data, test_data = get_dataset(data_name)

    # == Model ==
    model = VAE(latent_size=2).to(device)

    # == optimizer ==
    criterion = bce_kld_loss
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    # == Main Loop ==
    max_acc = 0
    max_epoch = 90
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
        plt.savefig('{}_vae_loss.png'.format(data_name))
        plt.cla()
        
        if epoch % 5 == 0:
            print('----- epoch {} -----'.format(epoch))
            torch.save(model.state_dict(), 'ckpts/e{:03}vae_{}.pt'.format(
                epoch, data_name))

            # sample
            sample = torch.randn(64, 2).to(device)
            sample = model.decode(sample).cpu()
            save_image(sample.view(64, 1, 28, 28),
                       'results/sample_e{:02}.png'.format(epoch))
            
            imgs = np.empty((28 * 20, 28 * 20))
            index_x = 0
            for x in range(-10,10,1):
                index_y = 0
                for y in range(-10,10,1):
                    value = np.array([[float(x / 5.), float(y / 5.)]])
                    img = model.decode(torch.Tensor(value).to(device)).cpu()
                    imgs[index_x * 28:(index_x + 1) * 28, index_y * 28:(index_y + 1) * 28] = img.view(28, 28).detach().numpy()
                    index_y += 1
                index_x += 1

            save_image(torch.Tensor(imgs), 'results/samples_e{:02}.png'.format(epoch))