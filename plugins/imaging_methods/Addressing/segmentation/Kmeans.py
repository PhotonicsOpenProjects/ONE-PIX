import cv2
import numpy as np

class Clustering:

    def __init__(self,clustering_parameters):
        self.clustering_parameters=clustering_parameters

    def kmeans_LAB(self,img,nb_clust):
        
        Z = img.reshape((-1,3))
        Z = np.float32(Z)
        
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        ret,label,center=cv2.kmeans(Z,nb_clust,None,criteria,10,cv2.KMEANS_RANDOM_CENTERS)

        center = np.uint8(center)
        res = center[label.flatten()]
        res2 = res.reshape((img.shape))
        res2=np.sum(res2,-1)
        cluster_values=np.unique(res2)
        masks=[]
        class_ids=[]
        i=1
        for clust_value in cluster_values :
            stack=np.zeros(np.shape(res2))
            stack[np.where(res2==clust_value)]=255
            masks.append(stack)
            class_ids.append("clust "+str(i))
            i=i+1
        masks=np.asarray(masks)
        return masks

    def k_means2gray(self,im):
        shape = im.shape
        im2 = im.reshape(shape[0],-1)
        b = np.zeros((shape[1]))
        for i in range(im2.shape[0]):
            b[im[i,:]!=0]=i
        return b.reshape(np.asarray(shape)[-1:])

    def get_clusters(self,IMG):
        #Niagara_means
        B = cv2.cvtColor(IMG, cv2.COLOR_BGR2RGB)
        B = cv2.cvtColor(B, cv2.COLOR_RGB2LAB)
        B[:,:,0] = B[:,:,0].mean()*np.ones(B[:,:,0].shape)
        IM = cv2.cvtColor(B, cv2.COLOR_LAB2RGB)
        (L,l, any) = IM.shape
        im = IM.reshape(-1,3)
        
        labels = np.ones(L*l)
        labels[:] = self.k_means2gray(self.kmeans_LAB(im[:],self.clustering_parameters[0]))
        fond = []
        fond.append(labels == np.bincount(np.int8(labels)).argmax())
        masks = [labels != np.bincount(np.int8(labels)).argmax()]
        #print(segm_settings[0])
        for i in self.clustering_parameters[1:]:
            #print(i)
            temp_mask = []
            for j in range(len(masks)):
                labels = -1 * np.ones(L*l)
                labels[masks[j]] = self.k_means2gray(self.kmeans_LAB(im[masks[j]], i))
                labels+=1 # to exclude commun labels with bg
                temp_mask += [labels == k for k in np.unique(labels) if k!=0]
            masks = temp_mask
        masks = fond + masks
        return np.asarray([np.uint8(255*masks[m]).reshape(L,l) for m in range(len(masks))])


