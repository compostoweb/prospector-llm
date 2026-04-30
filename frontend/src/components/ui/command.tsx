"use client"

import * as React from "react"
import { Command as CommandPrimitive } from "cmdk"
import { Search } from "lucide-react"
import { cn } from "@/lib/utils"

const Command = React.forwardRef<
  React.ComponentRef<typeof CommandPrimitive>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive>
>(({ className, ...props }, ref) => (
  <CommandPrimitive
    ref={ref}
    className={cn(
      "flex flex-col overflow-hidden rounded-md bg-(--bg-surface) text-(--text-primary)",
      className,
    )}
    {...props}
  />
))
Command.displayName = CommandPrimitive.displayName

const CommandInput = React.forwardRef<
  React.ComponentRef<typeof CommandPrimitive.Input>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Input>
>(({ className, ...props }, ref) => (
  <div
    className="flex items-center gap-2 border-b border-(--border-default) px-3 focus-within:outline-none focus-within:ring-0 focus-within:shadow-none"
    cmdk-input-wrapper=""
  >
    <Search size={13} className="shrink-0 text-(--text-secondary)" />
    <CommandPrimitive.Input
      ref={ref}
      style={{
        border: "none",
        outline: "none",
        boxShadow: "none",
      }}
      className={cn(
        "flex h-9 w-full appearance-none border-0 border-l-0 border-r-0 bg-transparent py-2 text-xs outline-none ring-0 shadow-none placeholder:text-(--text-secondary) placeholder:opacity-100 disabled:cursor-not-allowed disabled:opacity-50 focus:border-0 focus:border-l-0 focus:border-r-0 focus:outline-none focus:ring-0 focus:shadow-none focus-visible:border-0 focus-visible:border-l-0 focus-visible:border-r-0 focus-visible:outline-none focus-visible:ring-0 focus-visible:shadow-none",
        className,
      )}
      {...props}
    />
  </div>
))
CommandInput.displayName = CommandPrimitive.Input.displayName

const CommandList = React.forwardRef<
  React.ComponentRef<typeof CommandPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.List>
>(({ className, ...props }, ref) => (
  <CommandPrimitive.List
    ref={ref}
    className={cn("max-h-60 overflow-y-auto overflow-x-hidden", className)}
    {...props}
  />
))
CommandList.displayName = CommandPrimitive.List.displayName

const CommandEmpty = React.forwardRef<
  React.ComponentRef<typeof CommandPrimitive.Empty>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Empty>
>((props, ref) => (
  <CommandPrimitive.Empty
    ref={ref}
    className="py-4 text-center text-xs text-(--text-secondary)"
    {...props}
  />
))
CommandEmpty.displayName = CommandPrimitive.Empty.displayName

const CommandItem = React.forwardRef<
  React.ComponentRef<typeof CommandPrimitive.Item>,
  React.ComponentPropsWithoutRef<typeof CommandPrimitive.Item>
>(({ className, ...props }, ref) => (
  <CommandPrimitive.Item
    ref={ref}
    className={cn(
      "relative flex cursor-pointer select-none items-center gap-2 rounded-sm px-3 py-1.5 text-xs outline-none",
      "text-(--text-secondary) transition-colors",
      "data-[selected=true]:bg-(--bg-overlay) data-[selected=true]:text-(--text-primary)",
      "data-[disabled=true]:pointer-events-none data-[disabled=true]:opacity-50",
      className,
    )}
    {...props}
  />
))
CommandItem.displayName = CommandPrimitive.Item.displayName

export { Command, CommandInput, CommandList, CommandEmpty, CommandItem }
