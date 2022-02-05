# Transport Planning with Commuting Demand

[TOC]

## 與paper不同的地方

### 1. The commuting demand that can be met by 𝜇

修改過後的(2)式：

$$ O_d(\mu) = \sum_{T_i \in D} \sum_{e \in T_i \cap \mu} |e| (max_{e' \in E}(|e'|) - |e|) 
$$

where $T_i \cap \mu$ denotes the common edges that $T_i$ and $\mu$ share, and $|e|$ denotes the *length* of edge $e \in E$, i.e. the length of the road segment.

### 2. 不考慮Connectivity

因此"Lanczos-based Connectivity Estimation"等等的東西通通用不上

## Input格式與內容

三個input分別是:
- Road Network
- Transit Network
- Trajectory Data

### Road Network

我預設road network資料是從OpenStreetMap取得的osm-xml檔，然後經過`osmnx`轉換輸出的GraphML格式檔案。並且所有路段都是雙向可行的，也就是會存成無向圖(`networkx.classes.graph.Graph`)。

``` python
G = # get graph using graph_from_point/graph_from_xml/...
G = osmnx.utils_graph.get_undirected(G)
osmnx.io.save_graphml(G, 'data/road.graphml')
# 先透過osmnx存成graphml，因為networkx的GraphML writer不支援<class 'shapely.geometry.linestring.LineString'>
G = nx.read_graphml('data/road.graphml')
# 然後才再用networkx轉成simple graph
G = nx.Graph(G)
nx.write_graphml(G, 'data/road.graphml')
```

Attributes:
- Edge
  - `length`: 路段的長度。
  - `demand`: Trajectory Data進來後，會計算所有trajectory中有幾個包含這個edge，結果會存在這個attribute裡。這可以加快(2)式的計算。也就是下式中的$n_e$
  - `score`: 將自己(這個edge)代入新的(2)式計算後的結果。
  - $e_i[\text{weighted demand}] = O_d(e_i)$

$$ \begin{aligned}
    O_d(\mu) & = \sum_{T_i \in D} \sum_{e \in T_i \cap \mu} |e| (max_{e' \in E}(|e'|) - |e|) \\
    & = \sum_{e \in \mu} n_e |e| (max_{e' \in E}(|e'|) - |e|) 
\end{aligned}
$$

$n_e$ is the number of trajectories in $D$ that has edge $e$.

### Transit Network

Transit Network一樣也是GraphML檔案，無向圖，node是車站，edge表示兩個車站在地理位置上的距離小於τ。

※ 原本paper裡是用edge表示兩個車站是至少一個公車路線中的相鄰車站，用以計算connectivity。兩個車站在地理位置上的距離小於τ和它們之間的路徑是另外存的，但這裡沒有要算connectivity，就直接存一起。

Attributes:
- Node
  - `road`: 這個車站位於road network中的哪一條edge上。它是一個2-element tuple of strings，因為road network的node是string。
  - `x`, `y`: 記錄車站實際的地理位置，`x`是經度、`y`是緯度
- Edge
  - `path`: 標記公車在兩個車站之間會走的路徑(如果照paper的做法，就是最短路徑)。從檔案讀進來時是我預設它是以空白字符分隔的一串road network的node。因為Road Netowork是無向的，但路徑有方向性，因此路徑的首尾兩端要包含端點Node的node。
      - exmaple: `('12345', '67890', {'path':'1111 222 333 44444 555 6666'})` 這個edge連接transit network的node `'12345'`和`'67890'`，並且`'12345'`這個node對應著road network上的`('1111', '222')`這個edge，`'67890'`則是對應`('555', '6666')`。它們之間的路徑是road network上的node序列: '1111'->'222'->'333'->'44444'->'555'->'6666'。

因為無法預測Transit Network的來源會是什麼，就當作所有attribute在輸入前都已經先預處理好了。

### Trajectory Data

Trajectory Data是非公車的通勤記錄(paper裡用的是計程車)的集合，用以表示人群的通勤需求。每一筆trajectory都是Road Netowork上的一個路徑。

Trajectory Data的格式預設是一個csv檔，有兩個column：`id`和`trajectory`。`id`是每一筆的編號，`trajectory`則和Transit Network的edge的`path`一樣，是以空白分隔的一串node id。

## 實作細節

- dataset的讀取/前處理
- 臨時的測試用dataset
- 主要演算法
- 輸出結果
- 其他

### dataset的讀取/前處理

因為測試時用的自產dataset直接就符合自己設計的資料格式(就上個section寫的東西)，不需要什麼處理。等實際的dataset來了之後看情況，如果轉換不麻煩，就直接讓資料進來之後轉成自己的格式，(然後`geo.py`裡的code可能也要改)。這樣主要演算法部份的就不用更改。如果轉換很麻煩那就再說。

### 臨時的測試用dataset

要測試的話只能臨時自產dataset，整個`maketestdata.py`就是做這個的。

因為自產dataset會需要用到，所以寫了`findshortestPath`和`findNeighbors`。考慮到transit network的neighbors以及它們之間的shortest path這些資訊dataset可能不會給，而是要自己找，所以這兩個放在`nets.py`裡面。


## 主要演算法

跟主要演算法有關的code都在`main.py`裡

### 1. 前處理: 計算"demand"和"score"

因為「轉換機制」，反正它就是某個公式算出來分數。由`computeDemand`處理，給road network加上"demand"和"score"。

### 2. Initialization

`getCandidateEdges`回傳$L_d$，因為不考慮connetivity，它同時也是$L_e$。我寫了一個class `SortedEdgeDemandList`來包它。

$K$設為transit network的node數量和candidate edges的總數取最小值。

Priority queue也寫了一個class `MyPQ`包住，在`pq.py`。

### 3. Expansion

進while loop後開始expansion，因為不考慮connectivity的關係，每一次expansion就是在鄰居中找在$L_d$裡面排最前的那個

一些狀況：
- 會發生beginning edge和ending edge是同一個的狀況，根據paper第3頁的註解4，頭尾相連的環形路線是允許的。所以`be == ee`的路線可作為$\mu$的候選路線，但不能expand。
- `computeAngle`是計算路線最未端的三個站點的實際地理位置依順序連接的兩個折線之間的夾角
- 與計算夾角和距離有關的函數(包含`computeAngle`)都放在`geo.py`，而因為我用的臨時自產dataset提供的坐標是經緯度，所以目前實作的內容都是當球面在算。實際的dataset來了之後看情況會再改。
- paper裡面給algorithm裡面`tn`和$\mu$的更新的先後順序很奇怪？

### 4. 輸出與視覺化

`out.py`裡的`outputResult`，測試時為了能較好看出程式問題而讓它輸出圖片。實際的輸出格式還待後續要求。