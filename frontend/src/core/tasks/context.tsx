import {
  createContext,
  useCallback,
  useContext,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

import type { Subtask } from "./types";

export interface SubtaskContextValue {
  tasks: Record<string, Subtask>;
  setTasks: Dispatch<SetStateAction<Record<string, Subtask>>>;
}

export const SubtaskContext = createContext<SubtaskContextValue>({
  tasks: {},
  setTasks: (() => undefined) as Dispatch<SetStateAction<Record<string, Subtask>>>,
});

export function SubtasksProvider({ children }: { children: React.ReactNode }) {
  const [tasks, setTasks] = useState<Record<string, Subtask>>({});
  return (
    <SubtaskContext.Provider value={{ tasks, setTasks }}>
      {children}
    </SubtaskContext.Provider>
  );
}

export function useSubtaskContext() {
  const context = useContext(SubtaskContext);
  if (context === undefined) {
    throw new Error(
      "useSubtaskContext must be used within a SubtaskContext.Provider",
    );
  }
  return context;
}

export function useSubtask(id: string) {
  const { tasks } = useSubtaskContext();
  return tasks[id];
}

export function useUpdateSubtask() {
  const { setTasks } = useSubtaskContext();
  const updateSubtask = useCallback(
    (task: Partial<Subtask> & { id: string }) => {
      setTasks((prev) => {
        const prevTask = (prev[task.id] ?? { id: task.id }) as Subtask;
        const nextTask = { ...prevTask, ...task } as Subtask;
        const keys = new Set([
          ...Object.keys(prevTask) as Array<keyof Subtask>,
          ...Object.keys(nextTask) as Array<keyof Subtask>,
        ]);
        for (const key of keys) {
          if (prevTask[key] !== nextTask[key]) {
            return {
              ...prev,
              [task.id]: nextTask,
            };
          }
        }
        return prev;
      });
    },
    [setTasks],
  );
  return updateSubtask;
}
