import { useEffect, useState } from 'react';

interface Block {
  id: number;
  gridX: number;
  gridY: number;
  targetGridX: number;
  targetGridY: number;
}

const GRID_SIZE = 8;
const CELL_SIZE = 120;
const MAX_BLOCKS = 12;

export const AnimatedBlocks = () => {
  const [blocks, setBlocks] = useState<Block[]>([]);

  useEffect(() => {
    // Start with one block in the center
    const centerX = Math.floor(GRID_SIZE / 2);
    const centerY = Math.floor(GRID_SIZE / 2);
    
    setBlocks([{
      id: 0,
      gridX: centerX,
      gridY: centerY,
      targetGridX: centerX,
      targetGridY: centerY,
    }]);

    // Duplication logic
    const duplicateInterval = setInterval(() => {
      setBlocks(prevBlocks => {
        if (prevBlocks.length >= MAX_BLOCKS) return prevBlocks;

        // Pick a random existing block to duplicate from
        const sourceBlock = prevBlocks[Math.floor(Math.random() * prevBlocks.length)];
        
        // Find adjacent empty cell
        const directions = [
          { dx: 0, dy: -1 }, // up
          { dx: 1, dy: 0 },  // right
          { dx: 0, dy: 1 },  // down
          { dx: -1, dy: 0 }, // left
        ];

        const shuffled = directions.sort(() => Math.random() - 0.5);
        
        for (const dir of shuffled) {
          const newX = sourceBlock.gridX + dir.dx;
          const newY = sourceBlock.gridY + dir.dy;
          
          if (newX >= 0 && newX < GRID_SIZE && newY >= 0 && newY < GRID_SIZE) {
            const occupied = prevBlocks.some(b => b.gridX === newX && b.gridY === newY);
            if (!occupied) {
              return [...prevBlocks, {
                id: prevBlocks.length,
                gridX: sourceBlock.gridX,
                gridY: sourceBlock.gridY,
                targetGridX: newX,
                targetGridY: newY,
              }];
            }
          }
        }
        
        return prevBlocks;
      });
    }, 800);

    // Movement logic - blocks randomly move to adjacent cells
    const moveInterval = setInterval(() => {
      setBlocks(prevBlocks => {
        return prevBlocks.map(block => {
          if (Math.random() > 0.3) return block; // 30% chance to move
          
          const directions = [
            { dx: 0, dy: -1 },
            { dx: 1, dy: 0 },
            { dx: 0, dy: 1 },
            { dx: -1, dy: 0 },
          ];
          
          const validMoves = directions.filter(dir => {
            const newX = block.gridX + dir.dx;
            const newY = block.gridY + dir.dy;
            return newX >= 0 && newX < GRID_SIZE && newY >= 0 && newY < GRID_SIZE &&
                   !prevBlocks.some(b => b !== block && b.targetGridX === newX && b.targetGridY === newY);
          });
          
          if (validMoves.length === 0) return block;
          
          const move = validMoves[Math.floor(Math.random() * validMoves.length)];
          return {
            ...block,
            targetGridX: block.gridX + move.dx,
            targetGridY: block.gridY + move.dy,
          };
        });
      });
    }, 2000);

    // Update actual positions to match targets
    const updateInterval = setInterval(() => {
      setBlocks(prevBlocks => 
        prevBlocks.map(block => ({
          ...block,
          gridX: block.targetGridX,
          gridY: block.targetGridY,
        }))
      );
    }, 100);

    return () => {
      clearInterval(duplicateInterval);
      clearInterval(moveInterval);
      clearInterval(updateInterval);
    };
  }, []);

  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0 flex items-center justify-center">
      <div className="relative" style={{ width: GRID_SIZE * CELL_SIZE, height: GRID_SIZE * CELL_SIZE }}>
        {blocks.map((block) => (
          <div
            key={block.id}
            className="absolute bg-accent rounded-sm transition-all duration-1000 ease-in-out"
            style={{
              left: `${block.targetGridX * CELL_SIZE}px`,
              top: `${block.targetGridY * CELL_SIZE}px`,
              width: `${CELL_SIZE - 10}px`,
              height: `${CELL_SIZE - 10}px`,
              opacity: 0.8,
            }}
          />
        ))}
      </div>
    </div>
  );
};
