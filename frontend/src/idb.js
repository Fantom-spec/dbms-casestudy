export const openDB = (name = "expense-tracker", version = 2) => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(name, version);
    request.onupgradeneeded = (e) => {
      const db = request.result;
      const store = db.objectStoreNames.contains("expenses")
        ? request.transaction.objectStore("expenses")
        : db.createObjectStore("expenses", { keyPath: "expense_id", autoIncrement: true });
      if (!store.indexNames.contains("synced")) store.createIndex("synced", "synced");
    };
    request.onsuccess = (e) => resolve(request.result);
    request.onerror = (e) => reject(e.target.error);
  });
};

export const getAllExpenses = async (db) => {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("expenses", "readonly");
    const store = tx.objectStore("expenses");
    const getAll = store.getAll();
    getAll.onsuccess = () => resolve(getAll.result);
    getAll.onerror = (e) => reject(e.target.error);
    tx.oncomplete = () => {};
  });
};

export const addExpense = async (db, expense) => {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("expenses", "readwrite");
    const store = tx.objectStore("expenses");
    const request = store.add({
      ...expense,
      synced: 0,
      updated_at: new Date().toISOString(),
    });
    request.onsuccess = () => resolve(request.result);
    request.onerror = (e) => reject(e.target.error);
    tx.oncomplete = () => {};
  });
};

export const updateExpense = async (db, expenseId, updates) => {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("expenses", "readwrite");
    const store = tx.objectStore("expenses");
    const request = store.get(expenseId);
    request.onsuccess = () => {
      const existing = request.result;
      if (!existing) return reject(new Error("Expense not found"));
      Object.assign(existing, updates);
      const updateReq = store.put(existing);
      updateReq.onsuccess = () => resolve(updateReq.result);
      updateReq.onerror = (e) => reject(e.target.error);
    };
    request.onerror = (e) => reject(e.target.error);
    tx.oncomplete = () => {};
  });
};

export const markSynced = async (db, expenseId) => {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("expenses", "readwrite");
    const store = tx.objectStore("expenses");
    const request = store.get(expenseId);
    request.onsuccess = () => {
      const existing = request.result;
      if (existing) {
        existing.synced = 1;
        existing.updated_at = new Date().toISOString();
        store.put(existing);
      }
    };
    tx.oncomplete = () => resolve();
    request.onerror = (e) => reject(e.target.error);
    tx.oncomplete = () => {};
  });
};

export const getPendingSyncCount = async (db) => {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("expenses", "readonly");
    const store = tx.objectStore("expenses");
    const index = store.index("synced");
    const request = index.getAll(0);
    request.onsuccess = () => resolve(request.result.length);
    request.onerror = (e) => reject(e.target.error);
    tx.oncomplete = () => {};
  });
};

export const removeExpense = async (db, expenseId) => {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("expenses", "readwrite");
    tx.objectStore("expenses").delete(expenseId);
    tx.oncomplete = () => resolve();
    tx.onerror = (e) => reject(e.target.error);
  });
};

export const clearAllSynced = async (db) => {
  return new Promise((resolve, reject) => {
    const tx = db.transaction("expenses", "readwrite");
    const store = tx.objectStore("expenses");
    const index = store.index("synced");
    const request = index.openCursor(IDBKeyRange.lowerBound(1));
    request.onsuccess = (e) => {
      const cursor = e.target.result;
      if (cursor) {
        cursor.delete();
        cursor.continue();
      } else {
        resolve();
      }
    };
    request.onerror = (e) => reject(e.target.error);
    tx.oncomplete = () => {};
  });
};