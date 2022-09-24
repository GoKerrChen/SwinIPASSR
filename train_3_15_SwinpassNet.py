# -*- coding: utf-8 -*-
"""train_3_15_SwinpassNet.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1A6YdpyCt0Tv8f-iF1MP2PY0SDkWj8Wyv
"""

# !git clone https://github.com/YingqianWang/iPASSR.git

from google.colab import drive
drive.mount('/content/drive')

# Commented out IPython magic to ensure Python compatibility.
# %cd /content/drive/MyDrive/Ntire/SwinIpass

!ls

from torch.autograd import Variable
from torch.utils.data import DataLoader
import torch.backends.cudnn as cudnn
import argparse
from utils import *
from model import *
from SwiniPassmodel import *

from PIL import Image
import os
from torch.utils.data.dataset import Dataset
import random
import torch
import numpy as np
import torchvision.transforms.functional as TF
from torchvision import transforms
import torchvision
from google.colab import files
from pathlib import Path
from torch.utils.tensorboard import SummaryWriter
from torchvision.transforms import ToTensor
from skimage.metrics import structural_similarity as ssim
import torch.nn.functional as F
import math

class TrainSetLoader(Dataset):
    def __init__(self, cfg):
        super(TrainSetLoader, self).__init__()
        self.dataset_dir = cfg.trainset_dir + '/HR/'
        self.file_list = sorted(os.listdir(self.dataset_dir))
        self.transform = transforms.Compose([transforms.ToTensor()])
    def __getitem__(self, index):
          lr_path = str(Path(self.dataset_dir).resolve().parent) + '/LR_x4/'
          hr_folder_img_left = Image.open(self.dataset_dir + self.file_list[index].split('_')[0] + '_' + 'L.png')
          hr_folder_img_right = Image.open(self.dataset_dir + self.file_list[index].split('_')[0] + '_' + 'R.png')
          
          lr_folder_img_left = Image.open(lr_path + self.file_list[index].split('_')[0] + '_' + 'L.png')
          lr_folder_img_right = Image.open(lr_path + self.file_list[index].split('_')[0] + '_' + 'R.png')
          #crop a patch with scale factor = 4
          i,j,h,w = transforms.RandomCrop.get_params(lr_folder_img_left, output_size = (30,90))

          left_lr = TF.crop(lr_folder_img_left, i, j, h, w)
          right_lr = TF.crop(lr_folder_img_right, i, j, h, w)
          left_hr = TF.crop(hr_folder_img_left, i*4, j*4, 4*h, 4*w)
          right_hr = TF.crop(hr_folder_img_right, i*4, j*4, 4*h, 4*w)

          img_hr_left, img_hr_right, img_lr_left, img_lr_right = augmentation(left_hr, right_hr, left_lr, right_lr)
          img_hr_left = self.transform(img_hr_left)
          img_hr_right = self.transform(img_hr_right)
          img_lr_left = self.transform(img_lr_left)
          img_lr_right = self.transform(img_lr_right)
          return img_hr_left, img_hr_right, img_lr_left, img_lr_right

    def __len__(self):
        return len(self.file_list)


def augmentation(hr_image_left, hr_image_right, lr_image_left, lr_image_right):
        augmentation_method = random.choice([0, 1, 2])     
        '''Vertical'''
        if augmentation_method == 0:
            vertical_flip = torchvision.transforms.RandomVerticalFlip(p=1)
            hr_image_left = vertical_flip(hr_image_left)
            hr_image_right = vertical_flip(hr_image_right)
            lr_image_left = vertical_flip(lr_image_left)
            lr_image_right = vertical_flip(lr_image_right)
            return hr_image_left, hr_image_right, lr_image_left, lr_image_right
        '''Horizontal'''
        if augmentation_method == 1:
            horizontal_flip = torchvision.transforms.RandomHorizontalFlip(p=1)
            hr_image_right = horizontal_flip(hr_image_left)
            hr_image_left = horizontal_flip(hr_image_right)
            lr_image_right = horizontal_flip(lr_image_left)
            lr_image_left = horizontal_flip(lr_image_right)
            return hr_image_left, hr_image_right, lr_image_left, lr_image_right
        '''no change'''
        if augmentation_method == 2:
            return hr_image_left, hr_image_right, lr_image_left, lr_image_right

"""### Model layer test"""

# !python /content/drive/MyDrive/Ntire/Swin_huan/network_swinir.py

# !python /content/drive/MyDrive/Ntire/SwinIpass/model.py

!python /content/drive/MyDrive/Ntire/SwinIpass/SwiniPassmodel.py

"""### data loader"""

class TestSetLoader(Dataset):
    def __init__(self, cfg_test):
        self.test_dir = cfg_test.testset_dir + '/HR/'
        self.file_list = sorted(os.listdir(self.test_dir))
        self.transform = transforms.Compose([transforms.ToTensor()])
    def __getitem__(self, index, is_train=False):
        lr_path = str(Path(self.test_dir).resolve().parent) + '/LR_x4/'
        hr_folder_img_left = Image.open(self.test_dir + self.file_list[index].split('_')[0] + '_' + 'L.png')
        hr_folder_img_right = Image.open(self.test_dir + self.file_list[index].split('_')[0] + '_' + 'R.png')  
        lr_folder_img_left = Image.open(lr_path + self.file_list[index].split('_')[0] + '_' + 'L.png')
        lr_folder_img_right = Image.open(lr_path + self.file_list[index].split('_')[0] + '_' + 'R.png')
        img_hr_left = self.transform(hr_folder_img_left)
        img_hr_right = self.transform(hr_folder_img_right)
        img_lr_left = self.transform(lr_folder_img_left)
        img_lr_right = self.transform(lr_folder_img_right)
        return img_hr_left, img_hr_right, img_lr_left, img_lr_right


    def __len__(self):
        return len(self.file_list)

"""### Train and Test args"""

def test_parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale_factor", type=int, default=4)
    parser.add_argument('--device', type=str, default='cuda:0')
    parser.add_argument('--batch_size', type=int, default=1)
    parser.add_argument('--testset_dir', type=str, default='/content/drive/MyDrive/Ntire/iPASSR_testset/Validation/')
    parser.add_argument('--model_name', type=str, default='SwiniPASSR_4xSR_epoch')
    return parser.parse_args(args=[])

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scale_factor", type=int, default=4)
    parser.add_argument('--device', type=str, default='cuda:0')
    parser.add_argument('--batch_size', type=int, default=2)
    parser.add_argument('--lr', type=float, default=2e-4, help='initial learning rate')
    parser.add_argument('--gamma', type=float, default=0.5, help='')
    parser.add_argument('--start_epoch', type=int, default=1, help='start epoch')
    parser.add_argument('--n_epochs', type=int, default=3000, help='number of epochs to train')
    parser.add_argument('--n_steps', type=int, default=1000, help='number of epochs to update learning rate')
    parser.add_argument('--trainset_dir', type=str, default='/content/drive/MyDrive/Ntire/Train')
    parser.add_argument('--model_name', type=str, default='SwiniPASSR_4xSR_epoch')
    parser.add_argument('--load_pretrain', type=bool, default=False)
    parser.add_argument('--model_path', type=str, default='/content/drive/MyDrive/Ntire/SwinIpass/log/3000_1000decay/SwiniPASSR_4xSR_epoch240.pth.tar')
    return parser.parse_args(args=[])

"""### SSIM Calculation"""

import torch
import torch.nn.functional as F
from math import exp
import numpy as np

def to_psnr(img, gt):
    mse = F.mse_loss(img, gt, reduction='none')
    mse_split = torch.split(mse, 1, dim=0)
    mse_list = [torch.mean(torch.squeeze(mse_split[ind])).item() for ind in range(len(mse_split))]
    intensity_max = 1.0
    psnr_list = [10.0 * math.log10(intensity_max / mse) for mse in mse_list]
    return psnr_list

def to_ssim_skimage(img, gt):
    sr_list = torch.split(img, 1, dim=0)
    gt_list = torch.split(gt, 1, dim=0)

    sr_list_np = [sr_list[ind].permute(0, 2, 3, 1).data.cpu().numpy().squeeze() for ind in range(len(sr_list))]
    gt_list_np = [gt_list[ind].permute(0, 2, 3, 1).data.cpu().numpy().squeeze() for ind in range(len(sr_list))]
    ssim_list = [ssim(sr_list_np[ind],  gt_list_np[ind]) for ind in range(len(sr_list))]

    return ssim_list

def gaussian(window_size, sigma):
    gauss = torch.Tensor([exp(-(x - window_size//2)**2/float(2*sigma**2)) for x in range(window_size)])
    return gauss/gauss.sum()


def create_window(window_size, channel=1):
    _1D_window = gaussian(window_size, 1.5).unsqueeze(1)
    _2D_window = _1D_window.mm(_1D_window.t()).float().unsqueeze(0).unsqueeze(0)
    window = _2D_window.expand(channel, 1, window_size, window_size).contiguous()
    return window


def ssim(img1, img2, window_size=11, window=None, size_average=True, full=False, val_range=None):
    # Value range can be different from 255. Other common ranges are 1 (sigmoid) and 2 (tanh).
    if val_range is None:
        if torch.max(img1) > 128:
            max_val = 255
        else:
            max_val = 1

        if torch.min(img1) < -0.5:
            min_val = -1
        else:
            min_val = 0
        L = max_val - min_val
    else:
        L = val_range

    padd = 0
    (_, channel, height, width) = img1.size()
    if window is None:
        real_size = min(window_size, height, width)
        window = create_window(real_size, channel=channel).to(img1.device)

    mu1 = F.conv2d(img1, window, padding=padd, groups=channel)
    mu2 = F.conv2d(img2, window, padding=padd, groups=channel)

    mu1_sq = mu1.pow(2)
    mu2_sq = mu2.pow(2)
    mu1_mu2 = mu1 * mu2

    sigma1_sq = F.conv2d(img1 * img1, window, padding=padd, groups=channel) - mu1_sq
    sigma2_sq = F.conv2d(img2 * img2, window, padding=padd, groups=channel) - mu2_sq
    sigma12 = F.conv2d(img1 * img2, window, padding=padd, groups=channel) - mu1_mu2

    C1 = (0.01 * L) ** 2
    C2 = (0.03 * L) ** 2

    v1 = 2.0 * sigma12 + C2
    v2 = sigma1_sq + sigma2_sq + C2
    cs = torch.mean(v1 / v2)  # contrast sensitivity

    ssim_map = ((2 * mu1_mu2 + C1) * v1) / ((mu1_sq + mu2_sq + C1) * v2)

    if size_average:
        ret = ssim_map.mean()
    else:
        ret = ssim_map.mean(1).mean(1).mean(1)

    if full:
        return ret, cs
    return ret


def msssim(img1, img2, window_size=11, size_average=True, val_range=None, normalize=False):
    device = img1.device
    weights = torch.FloatTensor([0.0448, 0.2856, 0.3001, 0.2363, 0.1333]).to(device)
    levels = weights.size()[0]
    mssim = []
    mcs = []
    for _ in range(levels):
        sim, cs = ssim(img1, img2, window_size=window_size, size_average=size_average, full=True, val_range=val_range)
        mssim.append(sim)
        mcs.append(cs)

        img1 = F.avg_pool2d(img1, (2, 2))
        img2 = F.avg_pool2d(img2, (2, 2))

    mssim = torch.stack(mssim)
    mcs = torch.stack(mcs)

    # Normalize (to avoid NaNs during training unstable models, not compliant with original definition)
    if normalize:
        mssim = (mssim + 1) / 2
        mcs = (mcs + 1) / 2

    pow1 = mcs ** weights
    pow2 = mssim ** weights
    # From Matlab implementation https://ece.uwaterloo.ca/~z70wang/research/iwssim/
    output = torch.prod(pow1[:-1] * pow2[-1])
    return output


# Classes to re-use window
class SSIM(torch.nn.Module):
    def __init__(self, window_size=11, size_average=True, val_range=None):
        super(SSIM, self).__init__()
        self.window_size = window_size
        self.size_average = size_average
        self.val_range = val_range

        # Assume 1 channel for SSIM
        self.channel = 1
        self.window = create_window(window_size)

    def forward(self, img1, img2):
        (_, channel, _, _) = img1.size()

        if channel == self.channel and self.window.dtype == img1.dtype:
            window = self.window
        else:
            window = create_window(self.window_size, channel).to(img1.device).type(img1.dtype)
            self.window = window
            self.channel = channel

        return ssim(img1, img2, window=window, window_size=self.window_size, size_average=self.size_average)

class MSSSIM(torch.nn.Module):
    def __init__(self, window_size=11, size_average=True, channel=3):
        super(MSSSIM, self).__init__()
        self.window_size = window_size
        self.size_average = size_average
        self.channel = channel

    def forward(self, img1, img2):
        # TODO: store window between calls if possible
        return msssim(img1, img2, window_size=self.window_size, size_average=self.size_average)

"""### Training"""

def train(train_loader, cfg, test_loader, cfg_test):
    net = SwinIR(cfg.scale_factor).to(cfg.device)
    cudnn.benchmark = True
    scale = cfg.scale_factor
    iteration = 0
    target_decay = cfg.n_steps
    
    # Set up tensorboard
    tensorboard_dir = cfg.model_name + str(cfg.n_epochs) + '_' + str(cfg.n_steps) + 'decay'
    if not os.path.exists(tensorboard_dir):
        os.makedirs(tensorboard_dir)
    print(tensorboard_dir)
    writer = SummaryWriter(os.path.join('/content/drive/MyDrive/Ntire/SwinIpass/Tensorboard/'+ tensorboard_dir))
    optimizer = torch.optim.Adam([paras for paras in net.parameters() if paras.requires_grad == True], lr=cfg.lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=cfg.n_steps, gamma=cfg.gamma)
    if cfg.load_pretrain:
        if os.path.isfile(cfg.model_path):
            model = torch.load(cfg.model_path, map_location={'cuda:0': cfg.device})
            net.load_state_dict(model['state_dict'])
            optimizer.load_state_dict(model['optimizer_state_dict'])
            loss = model['loss']
            scheduler.load_state_dict(model['scheduler_state_dict'])
            cfg.start_epoch = scheduler.last_epoch+1
            print(model['scheduler_state_dict'])
            # start = 990, 1000 decay then we want now n_steps = 10 to do the first decay
            # if cfg.start_epoch <= cfg.n_steps:
            #     cfg.n_steps = cfg.n_steps - cfg.start_epoch
            # else:
            #   # start = 900, 400decay 900%400=100, 400-100 = 300 steps need to go
            #     cfg.n_steps = cfg.n_steps - cfg.start_epoch % cfg.n_steps          
        else:
            print("=> no model found at '{}'".format(cfg.load_model))
    # else:
    #   # net = torch.nn.DataParallel(net, device_ids=[0, 1])
    #     optimizer = torch.optim.Adam([paras for paras in net.parameters() if paras.requires_grad == True], lr=cfg.lr)
    
    criterion_L1 = torch.nn.L1Loss().to(cfg.device)
    

    loss_epoch = []
    loss_list = []
    best_psnr_list = []
    net.train()
    for idx_epoch in range(cfg.start_epoch, cfg.n_epochs+1):
        # if idx_epoch != 0 and idx_epoch % target_decay == 0:
        #     cfg.n_steps = target_decay
        # if idx_epoch != 1 and idx_epoch % target_decay == 1:
          # need to change back to correct steps after n_steps as we want to keep first modified n_steps works first
          # else decay will never happen, eg 1000 start epoch 600 decay, first we want meet 600*2 to decay, but we need to change the n_steps
          # when 1201 epoch as 1200 epoch just meet the modified n_steps = 200.
            # scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=cfg.n_steps, gamma=cfg.gamma)
        current_lr = scheduler.get_last_lr()
        print('current_lr', current_lr)
        
        for idx_iter, (HR_left, HR_right, LR_left, LR_right) in enumerate(train_loader):
            iteration += 1 

            b, c, h, w = LR_left.shape
            # print('LR_left.shape',LR_left.shape)
            HR_left, HR_right, LR_left, LR_right  = Variable(HR_left).to(cfg.device), Variable(HR_right).to(cfg.device),\
                                                    Variable(LR_left).to(cfg.device), Variable(LR_right).to(cfg.device)
            
            SR_left, SR_right, (M_right_to_left, M_left_to_right), (V_left, V_right)\
                = net(LR_left, LR_right, is_training=1)
            # print('V_left',V_left.shape)
            # dimension = [1, 12, 32, 96]
            # b, c, h, w = dimension[0],dimension[1],dimension[2],dimension[3]
            ''' SR Loss '''
            loss_SR = criterion_L1(SR_left, HR_left) + criterion_L1(SR_right, HR_right)

            # ''' Photometric Loss '''
            # Res_left = torch.abs(HR_left - F.interpolate(LR_left, scale_factor=scale, mode='bicubic', align_corners=False))
            # Res_left = F.interpolate(Res_left, scale_factor=1 / scale, mode='bicubic', align_corners=False)
            # Res_right = torch.abs(HR_right - F.interpolate(LR_right, scale_factor=scale, mode='bicubic', align_corners=False))
            # Res_right = F.interpolate(Res_right, scale_factor=1 / scale, mode='bicubic', align_corners=False)
            

            # Res_leftT = torch.bmm(M_right_to_left.contiguous().view(b * h, w, w), Res_right.permute(0, 2, 3, 1).contiguous().view(b * h, w, c)
            #                       ).view(b, h, w, c).contiguous().permute(0, 3, 1, 2)
            # Res_rightT = torch.bmm(M_left_to_right.contiguous().view(b * h, w, w), Res_left.permute(0, 2, 3, 1).contiguous().view(b * h, w, c)
            #                        ).view(b, h, w, c).contiguous().permute(0, 3, 1, 2)
            # loss_photo = criterion_L1(Res_left * V_left.repeat(1, 3, 1, 1), Res_leftT * V_left.repeat(1, 3, 1, 1)) + \
            #              criterion_L1(Res_right * V_right.repeat(1, 3, 1, 1), Res_rightT * V_right.repeat(1, 3, 1, 1))

            # ''' Smoothness Loss '''
            # loss_h = criterion_L1(M_right_to_left[:, :-1, :, :], M_right_to_left[:, 1:, :, :]) + \
            #          criterion_L1(M_left_to_right[:, :-1, :, :], M_left_to_right[:, 1:, :, :])
            # loss_w = criterion_L1(M_right_to_left[:, :, :-1, :-1], M_right_to_left[:, :, 1:, 1:]) + \
            #          criterion_L1(M_left_to_right[:, :, :-1, :-1], M_left_to_right[:, :, 1:, 1:])
            # loss_smooth = loss_w + loss_h

            # ''' Cycle Loss '''
            # Res_left_cycle = torch.bmm(M_right_to_left.contiguous().view(b * h, w, w), Res_rightT.permute(0, 2, 3, 1).contiguous().view(b * h, w, c)
            #                            ).view(b, h, w, c).contiguous().permute(0, 3, 1, 2)
            # Res_right_cycle = torch.bmm(M_left_to_right.contiguous().view(b * h, w, w), Res_leftT.permute(0, 2, 3, 1).contiguous().view(b * h, w, c)
            #                             ).view(b, h, w, c).contiguous().permute(0, 3, 1, 2)
            # loss_cycle = criterion_L1(Res_left * V_left.repeat(1, 3, 1, 1), Res_left_cycle * V_left.repeat(1, 3, 1, 1)) + \
            #              criterion_L1(Res_right * V_right.repeat(1, 3, 1, 1), Res_right_cycle * V_right.repeat(1, 3, 1, 1))

            # ''' Consistency Loss '''
            # SR_left_res = F.interpolate(torch.abs(HR_left - SR_left), scale_factor=1 / scale, mode='bicubic', align_corners=False)
            # SR_right_res = F.interpolate(torch.abs(HR_right - SR_right), scale_factor=1 / scale, mode='bicubic', align_corners=False)
            # SR_left_resT = torch.bmm(M_right_to_left.detach().contiguous().view(b * h, w, w), SR_right_res.permute(0, 2, 3, 1).contiguous().view(b * h, w, c)
            #                          ).view(b, h, w, c).contiguous().permute(0, 3, 1, 2)
            # SR_right_resT = torch.bmm(M_left_to_right.detach().contiguous().view(b * h, w, w), SR_left_res.permute(0, 2, 3, 1).contiguous().view(b * h, w, c)
            #                           ).view(b, h, w, c).contiguous().permute(0, 3, 1, 2)
            # loss_cons = criterion_L1(SR_left_res * V_left.repeat(1, 3, 1, 1), SR_left_resT * V_left.repeat(1, 3, 1, 1)) + \
            #            criterion_L1(SR_right_res * V_right.repeat(1, 3, 1, 1), SR_right_resT * V_right.repeat(1, 3, 1, 1))

            ''' Total Loss '''
            # loss = loss_SR + 0.1 * loss_cons + 0.1 * (loss_photo + loss_smooth + loss_cycle)
            loss = loss_SR
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            # Load data to the tensorboard
            writer.add_scalars('training', {'training total loss': loss.item()
                                        }, iteration)
            # writer.add_scalars('training_img', {'SR_loss': loss_SR.item(),
            #                     'consist_loss': loss_cons.item(),
            #                     'loss_photo': loss_photo.item(),
            #                     'loss_smooth': loss_smooth.item(),
            #                     'loss_cycle': loss_cycle.item()}, iteration) 
            # writer.add_scalars('training_img', {'SR_loss': loss_SR.item()},
                                #  iteration) 
            
            loss_epoch.append(loss.data.cpu())

        scheduler.step()
        loss_list.append(float(np.array(loss_epoch).mean()))

        # print('Epoch--%4d, loss--%f, loss_SR--%f, loss_photo--%f, loss_smooth--%f, loss_cycle--%f, loss_cons--%f' %
        #       (idx_epoch, float(np.array(loss_epoch).mean()), float(np.array(loss_SR.data.cpu()).mean()),
        #       float(np.array(loss_photo.data.cpu()).mean()), float(np.array(loss_smooth.data.cpu()).mean()),
        #       float(np.array(loss_cycle.data.cpu()).mean()), float(np.array(loss_cons.data.cpu()).mean())))
        print('Epoch--%4d, loss--%f' %
              (idx_epoch, float(np.array(loss.data.cpu()).mean())))
        
        # loss_epoch = []
        # save the model before the learning rate decay， nsteps = 800, we save only on every epoch = 800-10
        # if idx_epoch % cfg.n_steps == cfg.n_steps - 10 and idx_epoch != 0:
        #     torch.save({'epoch': idx_epoch, 'state_dict': net.state_dict()},
        #       '/content/drive/MyDrive/Ntire/iPASSR-main/log/' + cfg.model_name + str(idx_epoch) + '.pth.tar')
        if idx_epoch % 10 == 0 and idx_epoch != 0:
            torch.save({'epoch': idx_epoch, 'state_dict': net.state_dict(),'optimizer_state_dict': optimizer.state_dict(), 'loss': loss, 'scheduler_state_dict': scheduler.state_dict()},
              '/content/drive/MyDrive/Ntire/SwinIpass/log/3000_1000decay/' + cfg.model_name + str(idx_epoch) + '.pth.tar')
            
        # start testing every 10 epochs    
        if idx_epoch % 10 == 0:          
            with torch.no_grad():
                left_psnr_list = []
                right_psnr_list = []
                left_ssim_list = []
                right_ssim_list = []
                avr_psnr_list = []
                avr_ssim_list = []
                
                net.eval()

                for idx_iter_test, (HR_left, HR_right, LR_left, LR_right) in enumerate(test_loader):
                    HR_left, HR_right, LR_left, LR_right  = Variable(HR_left).to(cfg_test.device), Variable(HR_right).to(cfg_test.device),\
                                                    Variable(LR_left).to(cfg_test.device), Variable(LR_right).to(cfg_test.device)           
                    SR_left, SR_right = net(LR_left, LR_right, is_training=0)
                    torch.cuda.empty_cache()
                    SR_left, SR_right = torch.clamp(SR_left, 0, 1), torch.clamp(SR_right, 0, 1)

                    # evaluation the PSNR and SSIM value of the model
                    left_psnr_list.extend(to_psnr(SR_left, HR_left))
                    right_psnr_list.extend(to_psnr(SR_right, HR_right))
                    # left_ssim_list.extend(to_ssim_skimage(SR_left, HR_left))
                    # right_ssim_list.extend(to_ssim_skimage(SR_right, HR_right))

                    one_psnr = np.array(left_psnr_list) + np.array(right_psnr_list)
                    # one_ssim = np.array(left_ssim_list) + np.array(right_ssim_list)

                    avr_psnr_list.extend(one_psnr/2)
                    # avr_ssim_list.extend(one_ssim/2)
                    
                avr_psnr = sum(avr_psnr_list)/len(avr_psnr_list)
                # avr_ssim = sum(avr_ssim_list)/len(avr_ssim_list)
               
                best_psnr_list.append(avr_psnr)
                
                print('reconstructed_avg_psnr: ', avr_psnr)

                writer.add_scalars('testing', {'testing_psnr':avr_psnr}, idx_epoch)
                # print('reconstructed_avg_ssim: ', avr_ssim)

                # writer.add_scalars('testing', {'testing_ssim': avr_ssim}, idx_epoch)
                    
    best_psnr = max(best_psnr_list)

    # index = 0 means epoch 10, index = 1 means epoch 
    if cfg.load_pretrain:
      best_epoch =(best_psnr_list.index(best_psnr)+1)*10 + cfg.start_epoch
    else:
      best_epoch = (best_psnr_list.index(best_psnr)+1)*10
    print('best_performance_epoch: ', best_epoch, ', avg_psnr: ', best_psnr)
    torch.save({'epoch': best_epoch, 'state_dict': net.state_dict(),'optimizer_state_dict': optimizer.state_dict(), 'loss': loss, 'scheduler.state_dict': scheduler.state_dict()},
              '/content/drive/MyDrive/Ntire/SwinIpass/log/3000_1000decay/' + cfg.model_name + str(best_epoch) + '.pth.tar')
    writer.close()

cfg = parse_args()
train_set = TrainSetLoader(cfg)
train_loader = DataLoader(dataset=train_set, num_workers=2, batch_size=cfg.batch_size, shuffle=True)

cfg_test = test_parse_args()
test_set = TestSetLoader(cfg_test)
test_loader = DataLoader(dataset=test_set)

# %cd /content/drive/MyDrive/Ntire/SwinIpass/log/
log_dir = '/content/drive/MyDrive/Ntire/SwinIpass/log/' + str(cfg.n_epochs) + '_' + str(cfg.n_steps) + 'decay'
if not os.path.exists(log_dir):
        os.makedirs(log_dir)
print(log_dir)

# Commented out IPython magic to ensure Python compatibility.
# %cd /content/drive/MyDrive/Ntire/SwinIpass/Tensorboard/
tensorboard_dir = cfg.model_name + str(cfg.n_epochs) + '_' + str(cfg.n_steps) + 'decay'
if not os.path.exists(tensorboard_dir):
        os.makedirs(tensorboard_dir)
# %load_ext tensorboard

# manually change the folder
# %tensorboard --logdir=/content/drive/MyDrive/Ntire/SwinIpass/Tensorboard/SwiniPASSR_4xSR_epoch3000_1000decay

train(train_loader, cfg, test_loader, cfg_test)

"""### Show one Batch of the Images"""

# def imshow(inp, title=None):
#     """imshow for Tensor."""
#     inp = inp.numpy().transpose((1, 2, 0))
#     inp = np.clip(inp, 0, 1)
#     plt.imshow(inp)


# # Get a batch of training data
# images = next(iter(train_loader))

# # Make a grid from batch
# output1 = torchvision.utils.make_grid(images[0])
# plt.imshow(output1.permute(1, 2, 0))

# # imshow(output)

# output2 = torchvision.utils.make_grid(images[1])
# plt.imshow(output2.permute(1, 2, 0))

# output3 = torchvision.utils.make_grid(images[2])
# plt.imshow(output3.permute(1, 2, 0))

# output4 = torchvision.utils.make_grid(images[3])
# plt.imshow(output4.permute(1, 2, 0))

# %cd /content/drive/MyDrive/Ntire/iPASSR-main/log

# from google.colab import files
# files.download('/content/iPASSR/log/iPASSR_4xSR_epoch' + cfg.n_epochs + '.pth.tar')

"""### Test after finishing Training"""

# def parse_args():
#     parser = argparse.ArgumentParser()
#     parser.add_argument('--testset_dir', type=str, default='/content/drive/MyDrive/Ntire/iPASSR_testset/Validation/')
#     parser.add_argument('--scale_factor', type=int, default=4)
#     parser.add_argument('--device', type=str, default='cuda:0')
#     parser.add_argument('--model_name', type=str, default='iPASSR_4xSR_epoch1950')
#     parser.add_argument('--n_epochs', type=int, default=200, help='number of epochs to train')
#     return parser.parse_args(args=[])

# def test(cfg):
#     net = Net(cfg.scale_factor).to(cfg.device)
#     model = torch.load('/content/drive/MyDrive/Ntire/iPASSR-main/log/' + cfg.model_name + '.pth.tar')
#     net.load_state_dict(model['state_dict'])
#     # sort all the files in the validation set in order to make it LR paire
#     file_list = sorted(os.listdir(cfg.testset_dir + '/LR_x4/'))
#     net.eval()
    
#     for idx in range(len(file_list)):
#         LR_left = Image.open(cfg.testset_dir + 'LR_x4/' + file_list[idx].split('_')[0] + '_' + 'L.png')
#         LR_right = Image.open(cfg.testset_dir + 'LR_x4/' + file_list[idx].split('_')[0] + '_' + 'R.png')

#         LR_left, LR_right = ToTensor()(LR_left), ToTensor()(LR_right)
#         LR_left, LR_right = LR_left.unsqueeze(0), LR_right.unsqueeze(0)
#         LR_left, LR_right = Variable(LR_left).to(cfg.device), Variable(LR_right).to(cfg.device)
        
#         scene_name = file_list[idx]
#         print('Running Scene ' + scene_name + ' of Flickr1024 Dataset......')
#         with torch.no_grad():
            
#             SR_left, SR_right = net(LR_left, LR_right, is_training=0)
#             SR_left, SR_right = torch.clamp(SR_left, 0, 1), torch.clamp(SR_right, 0, 1)

#         save_path = '/content/drive/MyDrive/Ntire/iPASSR_testset/results/' + cfg.model_name + '/Flickr1024'

#         if not os.path.exists(save_path):
#             os.makedirs(save_path)

#         SR_left_img = transforms.ToPILImage()(torch.squeeze(SR_left.data.cpu(), 0))
#         SR_right_img = transforms.ToPILImage()(torch.squeeze(SR_right.data.cpu(), 0))

#         SR_left_img.save(save_path + '/' + file_list[idx].split('_')[0] + '_' + 'L.png')
#         SR_right_img.save(save_path + '/' + file_list[idx].split('_')[0] + '_' + 'R.png')

# cfg_test = parse_args()
# test(cfg_test)
# print('Finished!')

"""### Tensorboard After Training"""

# LOG_DIR = '/content/drive/MyDrive/Ntire/iPASSR-main/log/Tensorboard/'+ tensorboard_dir
# get_ipython().system_raw('tensorboard --logdir {} --host 0.0.0.0 --port 6006 &'.format(LOG_DIR))
# # Install

# !npm install -g localtunnel
# # Tunnel port 6006 (TensorBoard assumed running)
# get_ipython().system_raw('lt --port 6006 >> url.txt 2>&1 &')
# # Get url
# !cat url.txt