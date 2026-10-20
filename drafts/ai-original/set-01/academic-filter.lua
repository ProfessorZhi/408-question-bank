-- Set 01 academic print formatter: options, readable code, vector artwork.
local function is_option(block, expected)
  if block.t ~= 'Para' and block.t ~= 'Plain' then return false end
  local first = block.content[1]
  if not first or first.t ~= 'Str' then return false end
  return first.text == expected .. '.' or first.text == expected .. '．'
end
local function latex_inlines(inlines)
  local data = {}
  for i = 2, #inlines do data[#data+1] = inlines[i] end
  if #data > 0 and data[1].t == 'Space' then table.remove(data, 1) end
  local frag = pandoc.Pandoc({pandoc.Plain(data)})
  return (pandoc.write(frag, 'latex'):gsub('^%s+', ''):gsub('%s+$', ''))
end
local function plain_inlines(inlines)
  local data = {}
  for i=2, #inlines do data[#data+1] = inlines[i] end
  return pandoc.utils.stringify(data)
end
function Blocks(blocks)
  local out = pandoc.List()
  local i = 1
  while i <= #blocks do
    if i+3 <= #blocks and is_option(blocks[i], 'A') and is_option(blocks[i+1], 'B')
       and is_option(blocks[i+2], 'C') and is_option(blocks[i+3], 'D') then
      local b, length = {}, 0
      for k=0,3 do
        b[#b+1] = latex_inlines(blocks[i+k].content)
        local plain = plain_inlines(blocks[i+k].content)
        local len = utf8.len(plain) or #plain
        if len > length then length = len end
      end
      local macro = (length > 31) and '\\ChoicesOne' or '\\ChoicesTwo'
      out:insert(pandoc.RawBlock('latex', macro..'{'..b[1]..'}{'..b[2]..'}{'..b[3]..'}{'..b[4]..'}'))
      i = i + 4
    else
      out:insert(blocks[i])
      i = i + 1
    end
  end
  return out
end
function CodeBlock(b)
  return pandoc.RawBlock('latex',
    '\\begin{Verbatim}[fontsize=\\footnotesize,frame=leftline,rulecolor=\\color{examLine},framesep=2mm,breaklines=true,breakanywhere=true]\n'
      .. b.text .. '\n\\end{Verbatim}')
end
function Figure(fig)
  local part = fig.content and fig.content[1]
  local img = part and part.content and part.content[1]
  if not img or img.t ~= 'Image' then return nil end
  local src = img.src:gsub('%.svg$', '.pdf')
  local id = src:match('q(%d+)%-%w+%.pdf$')
  if not id then return nil end
  local name = '图 ' .. tonumber(id)
  if src:find('answer') then name = name .. '（参考解答）' end
  local width = '0.90'
  if src:find('q07') or src:find('q42-avl') then width='0.68' end
  if src:find('q35') or src:find('q45') then width='0.79' end
  if src:find('q41') then width='0.96' end
  return pandoc.RawBlock('latex', '\\ExamFigure{'..src..'}{'..width..'}{'..name..'}')
end
