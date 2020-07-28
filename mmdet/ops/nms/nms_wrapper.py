import numpy as np
import torch

from . import nms_cpu, nms_cuda
from .soft_nms_cpu import soft_nms_cpu

from . import oks_nms_py, oks_nms_cuda, oks_nms_cpu, oks_nms_vis_cuda


def nms(dets, iou_thr, device_id=None):
    """Dispatch to either CPU or GPU NMS implementations.

    The input can be either a torch tensor or numpy array. GPU NMS will be used
    if the input is a gpu tensor or device_id is specified, otherwise CPU NMS
    will be used. The returned type will always be the same as inputs.

    Arguments:
        dets (torch.Tensor or np.ndarray): bboxes with scores.
        iou_thr (float): IoU threshold for NMS.
        device_id (int, optional): when `dets` is a numpy array, if `device_id`
            is None, then cpu nms is used, otherwise gpu_nms will be used.

    Returns:
        tuple: kept bboxes and indice, which is always the same data type as
            the input.

    Example:
        >>> dets = np.array([[49.1, 32.4, 51.0, 35.9, 0.9],
        >>>                  [49.3, 32.9, 51.0, 35.3, 0.9],
        >>>                  [49.2, 31.8, 51.0, 35.4, 0.5],
        >>>                  [35.1, 11.5, 39.1, 15.7, 0.5],
        >>>                  [35.6, 11.8, 39.3, 14.2, 0.5],
        >>>                  [35.3, 11.5, 39.9, 14.5, 0.4],
        >>>                  [35.2, 11.7, 39.7, 15.7, 0.3]], dtype=np.float32)
        >>> iou_thr = 0.7
        >>> supressed, inds = nms(dets, iou_thr)
        >>> assert len(inds) == len(supressed) == 3
    """
    # convert dets (tensor or numpy array) to tensor
    if isinstance(dets, torch.Tensor):
        is_numpy = False
        dets_th = dets
    elif isinstance(dets, np.ndarray):
        is_numpy = True
        device = 'cpu' if device_id is None else 'cuda:{}'.format(device_id)
        dets_th = torch.from_numpy(dets).to(device)
    else:
        raise TypeError(
            'dets must be either a Tensor or numpy array, but got {}'.format(
                type(dets)))

    # execute cpu or cuda nms
    if dets_th.shape[0] == 0:
        inds = dets_th.new_zeros(0, dtype=torch.long)
    else:
        if dets_th.is_cuda:
            inds = nms_cuda.nms(dets_th, iou_thr)
        else:
            inds = nms_cpu.nms(dets_th, iou_thr)

    if is_numpy:
        inds = inds.cpu().numpy()
    return dets[inds, :], inds


def soft_nms(dets, iou_thr, method='linear', sigma=0.5, min_score=1e-3):
    """
    Example:
        >>> dets = np.array([[4., 3., 5., 3., 0.9],
        >>>                  [4., 3., 5., 4., 0.9],
        >>>                  [3., 1., 3., 1., 0.5],
        >>>                  [3., 1., 3., 1., 0.5],
        >>>                  [3., 1., 3., 1., 0.4],
        >>>                  [3., 1., 3., 1., 0.0]], dtype=np.float32)
        >>> iou_thr = 0.7
        >>> supressed, inds = soft_nms(dets, iou_thr, sigma=0.5)
        >>> assert len(inds) == len(supressed) == 3
    """
    if isinstance(dets, torch.Tensor):
        is_tensor = True
        dets_np = dets.detach().cpu().numpy()
    elif isinstance(dets, np.ndarray):
        is_tensor = False
        dets_np = dets
    else:
        raise TypeError(
            'dets must be either a Tensor or numpy array, but got {}'.format(
                type(dets)))

    method_codes = {'linear': 1, 'gaussian': 2}
    if method not in method_codes:
        raise ValueError('Invalid method for SoftNMS: {}'.format(method))
    new_dets, inds = soft_nms_cpu(
        dets_np,
        iou_thr,
        method=method_codes[method],
        sigma=sigma,
        min_score=min_score)

    if is_tensor:
        return dets.new_tensor(new_dets), dets.new_tensor(
            inds, dtype=torch.long)
    else:
        return new_dets.astype(np.float32), inds.astype(np.int64)


def oks_nms(kpts, iou_thr, sigmas, device_id=None):
    """Dispatch to either CPU or GPU NMS implementations.

    The input can be either a torch tensor or numpy array. GPU NMS will be used
    if the input is a gpu tensor or device_id is specified, otherwise CPU NMS
    will be used. The returned type will always be the same as inputs.

    Arguments:
        dets (torch.Tensor or np.ndarray): bboxes with scores.
        iou_thr (float): IoU threshold for NMS.
        device_id (int, optional): when `dets` is a numpy array, if `device_id`
            is None, then cpu nms is used, otherwise gpu_nms will be used.

    Returns:
        tuple: kept bboxes and indice, which is always the same data type as
            the input.
    """
    # convert dets (tensor or numpy array) to tensor
    sigmas = [s/10 for s in sigmas]
    sigmas = torch.FloatTensor(sigmas)
    if isinstance(kpts, torch.Tensor):
        is_numpy = False
        kpts_th = kpts
    elif isinstance(kpts, np.ndarray):
        is_numpy = True
        device = 'cpu' if device_id is None else 'cuda:{}'.format(device_id)
        kpts_th = torch.from_numpy(kpts).to(device)
    else:
        raise TypeError(
            'kpts must be either a Tensor or numpy array, but got {}'.format(
                type(kpts)))

    # execute cpu or cuda nms
    if kpts_th.shape[0] == 0:
        inds = kpts_th.new_zeros(0, dtype=torch.long)
    else:
        if kpts_th.is_cuda:
            inds = oks_nms_cuda.oks_nms(kpts_th, iou_thr, sigmas)
        else:
            inds = oks_nms_cpu.oks_nms(kpts_th, iou_thr, sigmas)
            inds_py = oks_nms_py.oks_nms(kpts_th.cpu().numpy(), iou_thr, sigmas.cpu().numpy())
        #test code for nms, cuda, cpu and python
        #time_start=time.time()
        #time_1=time.time()
        #print('time cuda  cost', time_1 - time_start,'s')
        #inds_c = oks_nms_cpu.oks_nms(kpts_th.cpu(), iou_thr, sigmas.cpu())
        #time_2=time.time()
        #print('time cpu cost', time_2 - time_1,'s')
        #inds_py = oks_nms_py.oks_nms(kpts_th.cpu().numpy(), iou_thr, sigmas.cpu().numpy())
        #time_3=time.time()
        #print('time py cost', time_3 - time_2,'s')
        #inter1 = [t for t in inds_c.numpy() if t not in inds.cpu().numpy()]
        #inter2 = [t for t in inds_py if t not in inds.cpu().numpy()]
        #pdb.set_trace()
    if is_numpy:
        inds = inds.cpu().numpy()
    return kpts[inds, :], inds


def oks_nms(kpts, iou_thr, sigmas, device_id=None):
    """Dispatch to either CPU or GPU NMS implementations.

    The input can be either a torch tensor or numpy array. GPU NMS will be used
    if the input is a gpu tensor or device_id is specified, otherwise CPU NMS
    will be used. The returned type will always be the same as inputs.

    Arguments:
        dets (torch.Tensor or np.ndarray): bboxes with scores.
        iou_thr (float): IoU threshold for NMS.
        device_id (int, optional): when `dets` is a numpy array, if `device_id`
            is None, then cpu nms is used, otherwise gpu_nms will be used.

    Returns:
        tuple: kept bboxes and indice, which is always the same data type as
            the input.
    """
    # convert dets (tensor or numpy array) to tensor
    sigmas = [s/10 for s in sigmas]
    sigmas = torch.FloatTensor(sigmas)
    if isinstance(kpts, torch.Tensor):
        is_numpy = False
        kpts_th = kpts
    elif isinstance(kpts, np.ndarray):
        is_numpy = True
        device = 'cpu' if device_id is None else 'cuda:{}'.format(device_id)
        kpts_th = torch.from_numpy(kpts).to(device)
    else:
        raise TypeError(
            'kpts must be either a Tensor or numpy array, but got {}'.format(
                type(kpts)))

    # execute cpu or cuda nms
    if kpts_th.shape[0] == 0:
        inds = kpts_th.new_zeros(0, dtype=torch.long)
    else:
        if kpts_th.is_cuda:
            inds = oks_nms_cuda.oks_nms(kpts_th, iou_thr, sigmas)
        else:
            inds = oks_nms_cpu.oks_nms(kpts_th, iou_thr, sigmas)
            inds_py = oks_nms_py.oks_nms(kpts_th.cpu().numpy(), iou_thr, sigmas.cpu().numpy())
        #test code for nms, cuda, cpu and python
        #time_start=time.time()
        #time_1=time.time()
        #print('time cuda  cost', time_1 - time_start,'s')
        #inds_c = oks_nms_cpu.oks_nms(kpts_th.cpu(), iou_thr, sigmas.cpu())
        #time_2=time.time()
        #print('time cpu cost', time_2 - time_1,'s')
        #inds_py = oks_nms_py.oks_nms(kpts_th.cpu().numpy(), iou_thr, sigmas.cpu().numpy())
        #time_3=time.time()
        #print('time py cost', time_3 - time_2,'s')
        #inter1 = [t for t in inds_c.numpy() if t not in inds.cpu().numpy()]
        #inter2 = [t for t in inds_py if t not in inds.cpu().numpy()]
        #pdb.set_trace()
    if is_numpy:
        inds = inds.cpu().numpy()
    return kpts[inds, :], inds


def oks_nms_vis(kpts, iou_thr, sigmas, vis_thr=0.1, device_id=None):
    """Dispatch to either CPU or GPU NMS implementations.

    The input can be either a torch tensor or numpy array. GPU NMS will be used
    if the input is a gpu tensor or device_id is specified, otherwise CPU NMS
    will be used. The returned type will always be the same as inputs.

    Arguments:
        dets (torch.Tensor or np.ndarray): bboxes with scores.
        iou_thr (float): IoU threshold for NMS.
        device_id (int, optional): when `dets` is a numpy array, if `device_id`
            is None, then cpu nms is used, otherwise gpu_nms will be used.

    Returns:
        tuple: kept bboxes and indice, which is always the same data type as
            the input.
    """
    # convert dets (tensor or numpy array) to tensor
    sigmas = [s/10 for s in sigmas]
    sigmas = torch.FloatTensor(sigmas)
    if isinstance(kpts, torch.Tensor):
        is_numpy = False
        kpts_th = kpts
    elif isinstance(kpts, np.ndarray):
        is_numpy = True
        device = 'cpu' if device_id is None else 'cuda:{}'.format(device_id)
        kpts_th = torch.from_numpy(kpts).to(device)
    else:
        raise TypeError(
            'kpts must be either a Tensor or numpy array, but got {}'.format(
                type(kpts)))

    # execute cpu or cuda nms
    if kpts_th.shape[0] == 0:
        inds = kpts_th.new_zeros(0, dtype=torch.long)
    else:
        if kpts_th.is_cuda:
            inds = oks_nms_vis_cuda.oks_nms(kpts_th, iou_thr, vis_thr, sigmas)
        else:
            inds = oks_nms_cpu.oks_nms(kpts_th, iou_thr, sigmas)
            inds_py = oks_nms_py.oks_nms(kpts_th.cpu().numpy(), iou_thr, sigmas.cpu().numpy())
        #test code for nms, cuda, cpu and python
        #time_start=time.time()
        #time_1=time.time()
        #print('time cuda  cost', time_1 - time_start,'s')
        #inds_c = oks_nms_cpu.oks_nms(kpts_th.cpu(), iou_thr, sigmas.cpu())
        #time_2=time.time()
        #print('time cpu cost', time_2 - time_1,'s')
        #inds_py = oks_nms_py.oks_nms(kpts_th.cpu().numpy(), iou_thr, sigmas.cpu().numpy())
        #time_3=time.time()
        #print('time py cost', time_3 - time_2,'s')
        #inter1 = [t for t in inds_c.numpy() if t not in inds.cpu().numpy()]
        #inter2 = [t for t in inds_py if t not in inds.cpu().numpy()]
        #pdb.set_trace()
    if is_numpy:
        inds = inds.cpu().numpy()
    return kpts[inds, :], inds